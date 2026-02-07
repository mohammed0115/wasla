from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from apps.accounts.models import AccountEmailOtp
from apps.accounts.application.services.otp_service import EmailOtpService
from apps.emails.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase


@dataclass(frozen=True)
class RequestEmailOtpCommand:
    user: AbstractBaseUser
    purpose: str = AccountEmailOtp.PURPOSE_EMAIL_VERIFY


@dataclass(frozen=True)
class RequestEmailOtpResult:
    otp_id: int
    expires_at: object


class RequestEmailOtpUseCase:
    @staticmethod
    def execute(cmd: RequestEmailOtpCommand) -> RequestEmailOtpResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")
        to_email = (getattr(cmd.user, "email", "") or "").strip()
        if not to_email:
            raise ValueError("User has no email.")
        issued = EmailOtpService.issue_otp(user=cmd.user, purpose=cmd.purpose)

        SendEmailUseCase.execute(
            SendEmailCommand(
                tenant_id=EmailOtpService.platform_tenant_id(),
                to_email=to_email,
                template_key="otp",
                context={"code": issued.code, "expires_minutes": 10},
                idempotency_key=f"otp:{cmd.user.id}:{cmd.purpose}:{issued.otp_id}",
                metadata={"event": "otp", "purpose": cmd.purpose, "user_id": str(cmd.user.id)},
            )
        )

        return RequestEmailOtpResult(otp_id=issued.otp_id, expires_at=issued.expires_at)
