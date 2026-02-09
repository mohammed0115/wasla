from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.errors import AccountAlreadyExistsError, AccountValidationError
from apps.accounts.domain.policies import ensure_terms_accepted, validate_email, validate_full_name, validate_phone
from apps.accounts.domain.state_machine import MerchantAuthStateMachine
from apps.accounts.models import AccountProfile, OnboardingProfile
from apps.accounts.services.audit_service import AccountAuditService
from apps.analytics.application.telemetry import TelemetryService, actor_from_user
from apps.analytics.domain.types import ObjectRef


@dataclass(frozen=True)
class RegisterMerchantCommand:
    full_name: str
    phone: str
    email: str
    password: str
    accept_terms: bool
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class RegisterMerchantResult:
    user: object
    otp_required: bool


class RegisterMerchantUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: RegisterMerchantCommand) -> RegisterMerchantResult:
        full_name = validate_full_name(cmd.full_name)
        phone = validate_phone(cmd.phone)
        email = validate_email(cmd.email)
        ensure_terms_accepted(bool(cmd.accept_terms))

        UserModel = get_user_model()
        if UserModel.objects.filter(username__iexact=phone).exists():
            raise AccountAlreadyExistsError("An account with this phone already exists.", field="phone")
        if UserModel.objects.filter(email__iexact=email).exists():
            raise AccountAlreadyExistsError("An account with this email already exists.", field="email")

        try:
            validate_password(cmd.password)
        except ValidationError as exc:
            raise AccountValidationError("; ".join(exc.messages), field="password") from exc

        user = UserModel.objects.create_user(
            username=phone,
            email=email,
            password=cmd.password,
        )
        AccountProfile.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            accepted_terms_at=timezone.now(),
        )
        OnboardingProfile.objects.get_or_create(user=user, defaults={"step": OnboardingProfile.STEP_REGISTERED})

        AccountAuditService.record_action(
            user=user,
            action=AccountAuditService.ACTION_REGISTERED,
            ip_address=cmd.ip_address,
            user_agent=cmd.user_agent,
            metadata={"email": email, "phone": phone},
        )
        TelemetryService.track(
            event_name="auth.registered",
            tenant_ctx=None,
            actor_ctx=actor_from_user(user=user, actor_type="MERCHANT"),
            object_ref=ObjectRef(object_type="USER", object_id=user.id),
            properties={"source": "register"},
        )

        otp_required = True
        _ = MerchantAuthStateMachine.next_step_after_register(otp_required=otp_required)
        return RegisterMerchantResult(user=user, otp_required=otp_required)
