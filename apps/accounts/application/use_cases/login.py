from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import authenticate

from apps.accounts.domain.errors import InvalidCredentialsError
from apps.accounts.domain.state_machine import MerchantAuthStateMachine
from apps.accounts.models import AccountProfile
from apps.tenants.models import StoreProfile, TenantMembership


@dataclass(frozen=True)
class LoginCommand:
    identifier: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    user: object
    otp_required: bool
    has_store: bool


class LoginUseCase:
    @staticmethod
    def execute(cmd: LoginCommand) -> LoginResult:
        identifier = (cmd.identifier or "").strip()
        if not identifier or not cmd.password:
            raise InvalidCredentialsError("Invalid credentials.")

        user = authenticate(username=identifier, password=cmd.password)
        if user is None:
            user = authenticate(username=identifier.lower(), password=cmd.password)

        if user is None:
            raise InvalidCredentialsError("Invalid credentials.")

        has_store = (
            TenantMembership.objects.filter(
                user=user,
                role=TenantMembership.ROLE_OWNER,
                is_active=True,
                tenant__is_active=True,
            ).exists()
            or StoreProfile.objects.filter(owner=user, tenant__is_active=True).exists()
        )
        profile = AccountProfile.objects.filter(user=user).first()
        has_email = bool((getattr(user, "email", "") or "").strip())
        otp_required = bool(profile and has_email and profile.email_verified_at is None)
        _ = MerchantAuthStateMachine.next_step_after_login(otp_required=otp_required, has_store=has_store)
        return LoginResult(user=user, otp_required=otp_required, has_store=has_store)
