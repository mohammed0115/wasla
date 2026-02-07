from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.hybrid_policies import is_testing_otp_allowed, test_otp_code, validate_identifier
from apps.accounts.domain.otp_policies_hybrid import OTP_MAX_ATTEMPTS, normalize_code, verify_otp
from apps.accounts.models import AccountProfile, OnboardingProfile, OTPChallenge, OTPLog


@dataclass(frozen=True)
class VerifyOtpCommand:
    identifier: str
    code: str
    channel: str = OTPChallenge.CHANNEL_EMAIL
    purpose: str = OTPChallenge.PURPOSE_LOGIN


@dataclass(frozen=True)
class VerifyOtpResult:
    user: object
    created: bool


class VerifyOtpUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: VerifyOtpCommand) -> VerifyOtpResult:
        identifier, id_type = validate_identifier(cmd.identifier)
        code = normalize_code(cmd.code)
        now = timezone.now()

        def _resolve_user() -> tuple[object, bool]:
            UserModel = get_user_model()
            if id_type == "email":
                user = UserModel.objects.filter(email__iexact=identifier).first()
            else:
                user = UserModel.objects.filter(username__iexact=identifier).first()

            created = False
            if not user:
                if id_type == "email":
                    user = UserModel.objects.create_user(username=identifier, email=identifier, password=None)
                else:
                    user = UserModel.objects.create_user(username=identifier, email="", password=None)
                created = True

            profile, _ = AccountProfile.objects.get_or_create(user=user)
            if id_type == "email" and not profile.email_verified_at:
                profile.email_verified_at = now
            if id_type == "phone" and not profile.phone:
                profile.phone = identifier
            profile.save(update_fields=["email_verified_at", "phone"])

            OnboardingProfile.objects.get_or_create(user=user, defaults={"step": OnboardingProfile.STEP_REGISTERED})
            return user, created

        if is_testing_otp_allowed() and code == test_otp_code():
            user, created = _resolve_user()
            OTPLog.objects.create(
                identifier=identifier,
                channel=cmd.channel,
                code_type=OTPLog.CODE_TYPE_TEST,
                verified_at=now,
            )
            return VerifyOtpResult(user=user, created=created)

        if len(code) != 6:
            raise ValueError("Invalid code.")

        challenge = (
            OTPChallenge.objects.select_for_update()
            .filter(
                identifier=identifier,
                channel=cmd.channel,
                purpose=cmd.purpose,
                consumed_at__isnull=True,
            )
            .order_by("-id")
            .first()
        )
        if not challenge:
            raise ValueError("No OTP requested.")
        if challenge.expires_at <= now:
            raise ValueError("OTP expired.")
        if challenge.attempt_count >= OTP_MAX_ATTEMPTS:
            raise ValueError("Too many attempts.")

        ok = verify_otp(otp_id=challenge.id, code=code, expected_hash=challenge.code_hash)
        if not ok:
            challenge.attempt_count = challenge.attempt_count + 1
            challenge.save(update_fields=["attempt_count"])
            raise ValueError("Invalid code.")

        challenge.consumed_at = now
        challenge.save(update_fields=["consumed_at"])

        user, created = _resolve_user()
        OTPLog.objects.create(
            identifier=identifier,
            channel=cmd.channel,
            code_type=OTPLog.CODE_TYPE_REAL,
            verified_at=now,
        )

        return VerifyOtpResult(user=user, created=created)
