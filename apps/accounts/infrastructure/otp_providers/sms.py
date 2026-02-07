from __future__ import annotations

from apps.accounts.domain.ports import OTPProviderPort, OtpSendResult
from apps.sms.application.use_cases.send_sms import SendSmsCommand, SendSmsUseCase


class SmsOtpProvider(OTPProviderPort):
    def send_otp(self, *, identifier: str, channel: str, code: str) -> OtpSendResult:
        body = f"Your verification code is {code}"
        SendSmsUseCase.execute(
            SendSmsCommand(
                body=body,
                recipients=[identifier],
                metadata={"event": "otp_hybrid", "channel": channel, "identifier": identifier},
            )
        )
        return OtpSendResult(delivered=True)
