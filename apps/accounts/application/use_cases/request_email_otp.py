from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.otp_policies import OTP_MAX_ATTEMPTS, generate_otp_code, hash_otp, otp_expires_at
from apps.accounts.models import AccountEmailOtp
from apps.emails.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase
from apps.tenants.models import Tenant


@dataclass(frozen=True)
class RequestEmailOtpCommand:
    user: AbstractBaseUser
    purpose: str = AccountEmailOtp.PURPOSE_EMAIL_VERIFY


@dataclass(frozen=True)
class RequestEmailOtpResult:
    otp_id: int
    expires_at: object


class RequestEmailOtpUseCase:
    PLATFORM_TENANT_SLUG = "default"

    @staticmethod
    def _platform_tenant_id() -> int:
        tenant = Tenant.objects.filter(slug=RequestEmailOtpUseCase.PLATFORM_TENANT_SLUG, is_active=True).first()
        return int(tenant.id) if tenant else 1

    @staticmethod
    @transaction.atomic
    def execute(cmd: RequestEmailOtpCommand) -> RequestEmailOtpResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")
        to_email = (getattr(cmd.user, "email", "") or "").strip()
        if not to_email:
            raise ValueError("User has no email.")

        # Reuse a recent unconsumed OTP if still valid and attempts not exhausted (avoid spamming + support retries).
        now = timezone.now()
        existing = (
            AccountEmailOtp.objects.select_for_update()
            .filter(
                user=cmd.user,
                purpose=cmd.purpose,
                consumed_at__isnull=True,
                expires_at__gt=now,
                attempt_count__lt=OTP_MAX_ATTEMPTS,
            )
            .order_by("-id")
            .first()
        )

        if existing:
            # Re-send with a new code to be safer (invalidate old by rotating hash + extending expiry).
            code = generate_otp_code()
            existing.expires_at = otp_expires_at()
            existing.code_hash = hash_otp(otp_id=existing.id, code=code)
            existing.last_sent_at = now
            existing.attempt_count = 0
            existing.save(update_fields=["expires_at", "code_hash", "last_sent_at", "attempt_count"])
            otp_id = existing.id
            expires_at = existing.expires_at
        else:
            otp = AccountEmailOtp.objects.create(
                user=cmd.user,
                purpose=cmd.purpose,
                code_hash="",
                expires_at=otp_expires_at(),
                last_sent_at=now,
            )
            code = generate_otp_code()
            otp.code_hash = hash_otp(otp_id=otp.id, code=code)
            otp.save(update_fields=["code_hash"])
            otp_id = otp.id
            expires_at = otp.expires_at

        SendEmailUseCase.execute(
            SendEmailCommand(
                tenant_id=RequestEmailOtpUseCase._platform_tenant_id(),
                to_email=to_email,
                template_key="otp",
                context={"code": code, "expires_minutes": 10},
                idempotency_key=f"otp:{cmd.user.id}:{cmd.purpose}:{otp_id}",
                metadata={"event": "otp", "purpose": cmd.purpose, "user_id": str(cmd.user.id)},
            )
        )

        return RequestEmailOtpResult(otp_id=otp_id, expires_at=expires_at)

