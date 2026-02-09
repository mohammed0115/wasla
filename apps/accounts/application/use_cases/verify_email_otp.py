from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.hybrid_policies import is_testing_otp_allowed, test_otp_code
from apps.accounts.domain.otp_policies import OTP_MAX_ATTEMPTS, normalize_code, verify_otp
from apps.accounts.models import AccountEmailOtp, AccountProfile, OTPChallenge, OTPLog
from apps.analytics.application.telemetry import TelemetryService, actor_from_user


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

        now = timezone.now()
        def _track_failed(reason_code: str) -> None:
            TelemetryService.track(
                event_name="auth.otp_failed",
                tenant_ctx=None,
                actor_ctx=actor_from_user(user=cmd.user, actor_type="MERCHANT"),
                properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": cmd.purpose, "reason_code": reason_code},
            )
        if is_testing_otp_allowed() and code == test_otp_code():
            if cmd.purpose == AccountEmailOtp.PURPOSE_EMAIL_VERIFY:
                AccountProfile.objects.filter(user=cmd.user, email_verified_at__isnull=True).update(email_verified_at=now)
            OTPLog.objects.create(
                identifier=(getattr(cmd.user, "email", "") or "").strip(),
                channel=OTPChallenge.CHANNEL_EMAIL,
                code_type=OTPLog.CODE_TYPE_TEST,
                verified_at=now,
            )
            TelemetryService.track(
                event_name="auth.otp_verified",
                tenant_ctx=None,
                actor_ctx=actor_from_user(user=cmd.user, actor_type="MERCHANT"),
                properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": cmd.purpose, "mode": "test"},
            )
            return VerifyEmailOtpResult(verified=True)

        if len(code) != 6:
            _track_failed("otp_invalid_format")
            raise ValueError("Invalid code.")
        otp = (
            AccountEmailOtp.objects.select_for_update()
            .filter(user=cmd.user, purpose=cmd.purpose, consumed_at__isnull=True)
            .order_by("-id")
            .first()
        )
        if not otp:
            _track_failed("otp_not_requested")
            raise ValueError("No OTP requested.")
        if otp.expires_at <= now:
            _track_failed("otp_expired")
            raise ValueError("OTP expired.")
        if otp.attempt_count >= OTP_MAX_ATTEMPTS:
            _track_failed("otp_too_many_attempts")
            raise ValueError("Too many attempts.")

        ok = verify_otp(otp_id=otp.id, code=code, expected_hash=otp.code_hash)
        if not ok:
            otp.attempt_count = otp.attempt_count + 1
            otp.save(update_fields=["attempt_count"])
            _track_failed("otp_wrong")
            raise ValueError("Invalid code.")

        otp.consumed_at = now
        otp.save(update_fields=["consumed_at"])

        if cmd.purpose == AccountEmailOtp.PURPOSE_EMAIL_VERIFY:
            AccountProfile.objects.filter(user=cmd.user, email_verified_at__isnull=True).update(email_verified_at=now)
        OTPLog.objects.create(
            identifier=(getattr(cmd.user, "email", "") or "").strip(),
            channel=OTPChallenge.CHANNEL_EMAIL,
            code_type=OTPLog.CODE_TYPE_REAL,
            verified_at=now,
        )
        TelemetryService.track(
            event_name="auth.otp_verified",
            tenant_ctx=None,
            actor_ctx=actor_from_user(user=cmd.user, actor_type="MERCHANT"),
            properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": cmd.purpose, "mode": "real"},
        )

        return VerifyEmailOtpResult(verified=True)
