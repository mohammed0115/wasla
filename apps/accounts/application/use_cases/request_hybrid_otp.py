from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.application.use_cases.request_otp import RequestOtpCommand, RequestOtpUseCase
from apps.accounts.domain.hybrid_policies import validate_identifier
from apps.accounts.models import OTPChallenge


@dataclass(frozen=True)
class RequestHybridOtpCommand:
    identifier: str
    purpose: str = OTPChallenge.PURPOSE_LOGIN
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class RequestHybridOtpResult:
    otp_id: int
    expires_at: object
    sent: bool
    identifier: str
    channel: str


class RequestHybridOtpUseCase:
    @staticmethod
    def execute(cmd: RequestHybridOtpCommand) -> RequestHybridOtpResult:
        identifier, id_type = validate_identifier(cmd.identifier)
        channel = OTPChallenge.CHANNEL_EMAIL if id_type == "email" else OTPChallenge.CHANNEL_SMS
        issued = RequestOtpUseCase.execute(
            RequestOtpCommand(
                identifier=identifier,
                channel=channel,
                purpose=cmd.purpose,
                ip_address=cmd.ip_address,
                user_agent=cmd.user_agent,
            )
        )
        return RequestHybridOtpResult(
            otp_id=issued.otp_id,
            expires_at=issued.expires_at,
            sent=issued.sent,
            identifier=issued.identifier,
            channel=channel,
        )
