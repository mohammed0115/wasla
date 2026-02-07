from __future__ import annotations

from apps.accounts.application.services.otp_service import EmailOtpService
from apps.accounts.domain.otp_policies_hybrid import OTP_TTL
from apps.accounts.domain.ports import OTPProviderPort, OtpSendResult
from apps.emails.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase


class EmailOtpProvider(OTPProviderPort):
    def send_otp(self, *, identifier: str, channel: str, code: str) -> OtpSendResult:
        expires_minutes = int(OTP_TTL.total_seconds() // 60)
        SendEmailUseCase.execute(
            SendEmailCommand(
                tenant_id=EmailOtpService.platform_tenant_id(),
                to_email=identifier,
                template_key="otp",
                context={"code": code, "expires_minutes": expires_minutes},
                idempotency_key=f"otp:hybrid:{identifier}:{code}",
                metadata={"event": "otp_hybrid", "channel": channel, "identifier": identifier},
            )
        )
        return OtpSendResult(delivered=True)
