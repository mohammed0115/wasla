from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OtpSendResult:
    delivered: bool


class OTPProviderPort:
    def send_otp(self, *, identifier: str, channel: str, code: str) -> OtpSendResult:  # pragma: no cover - interface
        raise NotImplementedError
