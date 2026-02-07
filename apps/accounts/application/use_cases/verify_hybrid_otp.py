from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.application.use_cases.verify_otp import VerifyOtpCommand, VerifyOtpUseCase
from apps.accounts.domain.hybrid_policies import validate_identifier
from apps.accounts.models import OTPChallenge


@dataclass(frozen=True)
class VerifyHybridOtpCommand:
    identifier: str
    code: str
    purpose: str = OTPChallenge.PURPOSE_LOGIN


@dataclass(frozen=True)
class VerifyHybridOtpResult:
    user: object
    created: bool
    channel: str


class VerifyHybridOtpUseCase:
    @staticmethod
    def execute(cmd: VerifyHybridOtpCommand) -> VerifyHybridOtpResult:
        _, id_type = validate_identifier(cmd.identifier)
        channel = OTPChallenge.CHANNEL_EMAIL if id_type == "email" else OTPChallenge.CHANNEL_SMS
        result = VerifyOtpUseCase.execute(
            VerifyOtpCommand(
                identifier=cmd.identifier,
                code=cmd.code,
                channel=channel,
                purpose=cmd.purpose,
            )
        )
        return VerifyHybridOtpResult(user=result.user, created=result.created, channel=channel)
