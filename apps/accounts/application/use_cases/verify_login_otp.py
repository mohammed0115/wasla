from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.accounts.application.services.identity_service import AccountIdentityService
from apps.accounts.domain.hybrid_policies import is_testing_otp_allowed, test_otp_code
from apps.accounts.domain.otp_policies import OTP_MAX_ATTEMPTS, normalize_code, verify_otp
from apps.accounts.models import AccountEmailOtp, AccountProfile, OTPChallenge, OTPLog
from apps.analytics.application.telemetry import TelemetryService
from apps.analytics.domain.types import ActorContext


@dataclass(frozen=True)
class VerifyLoginOtpCommand:
    identifier: str
    code: str


@dataclass(frozen=True)
class VerifyLoginOtpResult:
    user: object
    verified: bool


class VerifyLoginOtpUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: VerifyLoginOtpCommand) -> VerifyLoginOtpResult:
        user = AccountIdentityService.resolve_user_by_identifier(identifier=cmd.identifier)
        code = normalize_code(cmd.code)

        now = timezone.now()
        def _track_failed(reason_code: str) -> None:
            TelemetryService.track(
                event_name="auth.otp_failed",
                tenant_ctx=None,
                actor_ctx=ActorContext(actor_type="MERCHANT", actor_id=getattr(user, "id", None)),
                properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": "login", "reason_code": reason_code},
            )
        if is_testing_otp_allowed() and code == test_otp_code():
            OTPLog.objects.create(
                identifier=(cmd.identifier or "").strip() or (getattr(user, "email", "") or "").strip(),
                channel=OTPChallenge.CHANNEL_EMAIL,
                code_type=OTPLog.CODE_TYPE_TEST,
                verified_at=now,
            )
            TelemetryService.track(
                event_name="auth.otp_verified",
                tenant_ctx=None,
                actor_ctx=ActorContext(actor_type="MERCHANT", actor_id=getattr(user, "id", None)),
                properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": "login", "mode": "test"},
            )
            TelemetryService.track(
                event_name="auth.login_succeeded",
                tenant_ctx=None,
                actor_ctx=ActorContext(actor_type="MERCHANT", actor_id=getattr(user, "id", None)),
                properties={"method": "otp"},
            )
            return VerifyLoginOtpResult(user=user, verified=True)

        if len(code) != 6:
            _track_failed("otp_invalid_format")
            raise ValueError("Invalid code.")
        otp = (
            AccountEmailOtp.objects.select_for_update()
            .filter(user=user, purpose=AccountEmailOtp.PURPOSE_LOGIN, consumed_at__isnull=True)
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

        AccountProfile.objects.filter(user=user, email_verified_at__isnull=True).update(email_verified_at=now)
        OTPLog.objects.create(
            identifier=(cmd.identifier or "").strip() or (getattr(user, "email", "") or "").strip(),
            channel=OTPChallenge.CHANNEL_EMAIL,
            code_type=OTPLog.CODE_TYPE_REAL,
            verified_at=now,
        )
        TelemetryService.track(
            event_name="auth.otp_verified",
            tenant_ctx=None,
            actor_ctx=ActorContext(actor_type="MERCHANT", actor_id=getattr(user, "id", None)),
            properties={"channel": OTPChallenge.CHANNEL_EMAIL, "purpose": "login", "mode": "real"},
        )
        TelemetryService.track(
            event_name="auth.login_succeeded",
            tenant_ctx=None,
            actor_ctx=ActorContext(actor_type="MERCHANT", actor_id=getattr(user, "id", None)),
            properties={"method": "otp"},
        )

        return VerifyLoginOtpResult(user=user, verified=True)
