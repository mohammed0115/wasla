from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.application.services.identity_service import AccountIdentityService
from apps.accounts.application.services.otp_service import EmailOtpService
from apps.accounts.domain.errors import AccountValidationError
from apps.accounts.models import AccountEmailOtp
from apps.emails.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase


@dataclass(frozen=True)
class RequestLoginOtpCommand:
    identifier: str


@dataclass(frozen=True)
class RequestLoginOtpResult:
    otp_id: int
    expires_at: object


class RequestLoginOtpUseCase:
    @staticmethod
    def execute(cmd: RequestLoginOtpCommand) -> RequestLoginOtpResult:
        user = AccountIdentityService.resolve_user_by_identifier(identifier=cmd.identifier)
        to_email = (getattr(user, "email", "") or "").strip()
        if not to_email:
            raise AccountValidationError("User has no email.", field="email")

        issued = EmailOtpService.issue_otp(user=user, purpose=AccountEmailOtp.PURPOSE_LOGIN)
        SendEmailUseCase.execute(
            SendEmailCommand(
                tenant_id=EmailOtpService.platform_tenant_id(),
                to_email=to_email,
                template_key="otp",
                context={"code": issued.code, "expires_minutes": 10},
                idempotency_key=f"otp:login:{user.id}:{issued.otp_id}",
                metadata={"event": "otp_login", "user_id": str(user.id)},
            )
        )
        return RequestLoginOtpResult(otp_id=issued.otp_id, expires_at=issued.expires_at)
