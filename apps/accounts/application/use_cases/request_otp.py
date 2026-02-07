from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.accounts.application.services.otp_provider_resolver import OTPProviderResolver
from apps.accounts.domain.hybrid_policies import validate_identifier, validate_otp_rules
from apps.accounts.domain.otp_policies_hybrid import generate_otp_code, hash_otp, otp_expires_at
from apps.accounts.models import OTPChallenge


@dataclass(frozen=True)
class RequestOtpCommand:
    identifier: str
    channel: str = OTPChallenge.CHANNEL_EMAIL
    purpose: str = OTPChallenge.PURPOSE_LOGIN
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class RequestOtpResult:
    otp_id: int
    expires_at: object
    sent: bool
    identifier: str


class RequestOtpUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: RequestOtpCommand) -> RequestOtpResult:
        identifier, _ = validate_identifier(cmd.identifier)
        now = timezone.now()

        recent_count = OTPChallenge.objects.filter(
            identifier=identifier, channel=cmd.channel, created_at__gte=now - timedelta(minutes=10)
        ).count()

        existing = (
            OTPChallenge.objects.select_for_update()
            .filter(
                identifier=identifier,
                channel=cmd.channel,
                purpose=cmd.purpose,
                consumed_at__isnull=True,
                expires_at__gt=now,
            )
            .order_by("-id")
            .first()
        )
        validate_otp_rules(
            recent_count=recent_count,
            has_active=bool(existing),
            attempts=existing.attempt_count if existing else 0,
        )

        if existing and existing.last_sent_at and existing.last_sent_at >= now - timedelta(minutes=10):
            return RequestOtpResult(
                otp_id=existing.id,
                expires_at=existing.expires_at,
                sent=False,
                identifier=identifier,
            )

        if existing:
            code = generate_otp_code()
            existing.code_hash = hash_otp(otp_id=existing.id, code=code)
            existing.expires_at = otp_expires_at()
            existing.last_sent_at = now
            existing.attempt_count = 0
            existing.save(update_fields=["code_hash", "expires_at", "last_sent_at", "attempt_count"])
            otp_id = existing.id
            expires_at = existing.expires_at
        else:
            challenge = OTPChallenge.objects.create(
                identifier=identifier,
                channel=cmd.channel,
                purpose=cmd.purpose,
                code_hash="",
                expires_at=otp_expires_at(),
                last_sent_at=now,
                ip_address=cmd.ip_address,
                user_agent=cmd.user_agent,
            )
            code = generate_otp_code()
            challenge.code_hash = hash_otp(otp_id=challenge.id, code=code)
            challenge.save(update_fields=["code_hash"])
            otp_id = challenge.id
            expires_at = challenge.expires_at

        provider = OTPProviderResolver.resolve(cmd.channel)
        _ = provider.send_otp(identifier=identifier, channel=cmd.channel, code=code)

        return RequestOtpResult(otp_id=otp_id, expires_at=expires_at, sent=True, identifier=identifier)
