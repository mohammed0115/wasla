from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.errors import AccountAlreadyExistsError, AccountValidationError
from apps.accounts.domain.policies import ensure_terms_accepted, validate_email, validate_full_name, validate_phone
from apps.accounts.models import AccountProfile
from apps.accounts.services.audit_service import AccountAuditService


@dataclass(frozen=True)
class CompleteMerchantProfileCommand:
    user: AbstractBaseUser
    full_name: str
    phone: str
    email: str
    password: str
    accept_terms: bool
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class CompleteMerchantProfileResult:
    user: object
    otp_required: bool


class CompleteMerchantProfileUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: CompleteMerchantProfileCommand) -> CompleteMerchantProfileResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise AccountValidationError("Authentication required.")

        full_name = validate_full_name(cmd.full_name)
        phone = validate_phone(cmd.phone)
        email = validate_email(cmd.email)
        ensure_terms_accepted(bool(cmd.accept_terms))

        UserModel = get_user_model()
        if UserModel.objects.filter(username__iexact=phone).exclude(pk=cmd.user.pk).exists():
            raise AccountAlreadyExistsError("An account with this phone already exists.", field="phone")
        if UserModel.objects.filter(email__iexact=email).exclude(pk=cmd.user.pk).exists():
            raise AccountAlreadyExistsError("An account with this email already exists.", field="email")
        if AccountProfile.objects.filter(phone__iexact=phone).exclude(user=cmd.user).exists():
            raise AccountAlreadyExistsError("An account with this phone already exists.", field="phone")

        try:
            validate_password(cmd.password, user=cmd.user)
        except ValidationError as exc:
            raise AccountValidationError("; ".join(exc.messages), field="password") from exc

        # Preserve existing identifiers when they are already set.
        if getattr(cmd.user, "email", "") and cmd.user.email.lower() != email.lower():
            raise AccountValidationError("Email does not match this account.", field="email")

        profile, _ = AccountProfile.objects.get_or_create(user=cmd.user)
        if profile.phone and profile.phone != phone:
            raise AccountValidationError("Phone does not match this account.", field="phone")

        update_fields: list[str] = []
        if not getattr(cmd.user, "email", ""):
            cmd.user.email = email
            update_fields.append("email")
        if getattr(cmd.user, "username", "") != phone:
            cmd.user.username = phone
            update_fields.append("username")
        cmd.user.set_password(cmd.password)
        update_fields.append("password")
        cmd.user.save(update_fields=list(dict.fromkeys(update_fields)))

        profile.full_name = full_name
        profile.phone = phone
        if not profile.accepted_terms_at:
            profile.accepted_terms_at = timezone.now()
        profile.save(update_fields=["full_name", "phone", "accepted_terms_at"])

        AccountAuditService.record_action(
            user=cmd.user,
            action=AccountAuditService.ACTION_REGISTERED,
            ip_address=cmd.ip_address,
            user_agent=cmd.user_agent,
            metadata={"email": email, "phone": phone, "completed": True},
        )

        otp_required = bool(profile.email_verified_at is None and (cmd.user.email or "").strip())
        return CompleteMerchantProfileResult(user=cmd.user, otp_required=otp_required)
