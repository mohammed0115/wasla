from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.otp_policies import OTP_MAX_ATTEMPTS, normalize_code, verify_otp
from apps.accounts.models import AccountEmailOtp, AccountProfile


@dataclass(frozen=True)
class VerifyEmailOtpCommand:
    user: AbstractBaseUser
    purpose: str = AccountEmailOtp.PURPOSE_EMAIL_VERIFY
    code: str = ""


@dataclass(frozen=True)
class VerifyEmailOtpResult:
    verified: bool


class VerifyEmailOtpUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: VerifyEmailOtpCommand) -> VerifyEmailOtpResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")
        code = normalize_code(cmd.code)
        if len(code) != 6:
            raise ValueError("Invalid code.")

        now = timezone.now()
        otp = (
            AccountEmailOtp.objects.select_for_update()
            .filter(user=cmd.user, purpose=cmd.purpose, consumed_at__isnull=True)
            .order_by("-id")
            .first()
        )
        if not otp:
            raise ValueError("No OTP requested.")
        if otp.expires_at <= now:
            raise ValueError("OTP expired.")
        if otp.attempt_count >= OTP_MAX_ATTEMPTS:
            raise ValueError("Too many attempts.")

        ok = verify_otp(otp_id=otp.id, code=code, expected_hash=otp.code_hash)
        if not ok:
            otp.attempt_count = otp.attempt_count + 1
            otp.save(update_fields=["attempt_count"])
            raise ValueError("Invalid code.")

        otp.consumed_at = now
        otp.save(update_fields=["consumed_at"])

        if cmd.purpose == AccountEmailOtp.PURPOSE_EMAIL_VERIFY:
            AccountProfile.objects.filter(user=cmd.user, email_verified_at__isnull=True).update(email_verified_at=now)

        return VerifyEmailOtpResult(verified=True)

