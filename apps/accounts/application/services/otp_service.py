from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.otp_policies import OTP_MAX_ATTEMPTS, generate_otp_code, hash_otp, otp_expires_at
from apps.accounts.models import AccountEmailOtp
from apps.tenants.models import Tenant


@dataclass(frozen=True)
class IssuedOtp:
    otp_id: int
    code: str
    expires_at: object


class EmailOtpService:
    PLATFORM_TENANT_SLUG = "default"

    @staticmethod
    def platform_tenant_id() -> int:
        tenant = Tenant.objects.filter(slug=EmailOtpService.PLATFORM_TENANT_SLUG, is_active=True).first()
        return int(tenant.id) if tenant else 1

    @staticmethod
    @transaction.atomic
    def issue_otp(*, user, purpose: str) -> IssuedOtp:
        now = timezone.now()
        existing = (
            AccountEmailOtp.objects.select_for_update()
            .filter(
                user=user,
                purpose=purpose,
                consumed_at__isnull=True,
                expires_at__gt=now,
                attempt_count__lt=OTP_MAX_ATTEMPTS,
            )
            .order_by("-id")
            .first()
        )

        if existing:
            code = generate_otp_code()
            existing.expires_at = otp_expires_at()
            existing.code_hash = hash_otp(otp_id=existing.id, code=code)
            existing.last_sent_at = now
            existing.attempt_count = 0
            existing.save(update_fields=["expires_at", "code_hash", "last_sent_at", "attempt_count"])
            return IssuedOtp(otp_id=existing.id, code=code, expires_at=existing.expires_at)

        otp = AccountEmailOtp.objects.create(
            user=user,
            purpose=purpose,
            code_hash="",
            expires_at=otp_expires_at(),
            last_sent_at=now,
        )
        code = generate_otp_code()
        otp.code_hash = hash_otp(otp_id=otp.id, code=code)
        otp.save(update_fields=["code_hash"])
        return IssuedOtp(otp_id=otp.id, code=code, expires_at=otp.expires_at)
