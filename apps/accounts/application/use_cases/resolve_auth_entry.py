from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.application.services.identity_service import AccountIdentityService
from apps.accounts.domain.auth_flow import AuthIdentifierType, AuthMethod, SocialProvider
from apps.accounts.domain.errors import AccountNotFoundError, AccountValidationError
from apps.accounts.domain.policies import normalize_email, normalize_phone


@dataclass(frozen=True)
class ResolveAuthEntryCommand:
    identifier: str


@dataclass(frozen=True)
class ResolveAuthEntryResult:
    account_exists: bool
    identifier: str
    identifier_type: AuthIdentifierType
    available_methods: list[str]
    default_method: str
    can_register: bool
    has_email: bool
    has_password: bool
    social_providers: list[str]


class ResolveAuthEntryUseCase:
    @staticmethod
    def execute(cmd: ResolveAuthEntryCommand) -> ResolveAuthEntryResult:
        raw = (cmd.identifier or "").strip()
        if not raw:
            raise AccountValidationError("Identifier is required.", field="identifier")

        if "@" in raw:
            identifier_type = AuthIdentifierType.EMAIL
            normalized = normalize_email(raw)
        else:
            identifier_type = AuthIdentifierType.PHONE
            normalized = normalize_phone(raw)

        social_providers = [SocialProvider.GOOGLE.value, SocialProvider.APPLE.value]
        try:
            user = AccountIdentityService.resolve_user_by_identifier(identifier=normalized)
        except AccountNotFoundError:
            return ResolveAuthEntryResult(
                account_exists=False,
                identifier=normalized,
                identifier_type=identifier_type,
                available_methods=[AuthMethod.OTP.value],
                default_method=AuthMethod.OTP.value,
                can_register=True,
                has_email=identifier_type == AuthIdentifierType.EMAIL,
                has_password=False,
                social_providers=social_providers,
            )

        has_email = bool((getattr(user, "email", "") or "").strip())
        has_password = bool(getattr(user, "has_usable_password", lambda: False)())

        available_methods: list[str] = []
        otp_available = identifier_type == AuthIdentifierType.PHONE or has_email
        if otp_available:
            available_methods.append(AuthMethod.OTP.value)
        if has_password:
            available_methods.append(AuthMethod.PASSWORD.value)

        default_method = ""
        if AuthMethod.OTP.value in available_methods:
            default_method = AuthMethod.OTP.value
        elif available_methods:
            default_method = available_methods[0]

        if not available_methods:
            raise AccountValidationError("No available login methods for this account.", field="identifier")

        return ResolveAuthEntryResult(
            account_exists=True,
            identifier=normalized,
            identifier_type=identifier_type,
            available_methods=available_methods,
            default_method=default_method,
            can_register=False,
            has_email=has_email,
            has_password=has_password,
            social_providers=social_providers,
        )
