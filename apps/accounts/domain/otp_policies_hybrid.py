from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from django.utils import timezone

OTP_TTL = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_DIGITS = 6


def otp_expires_at():
    return timezone.now() + OTP_TTL


def _otp_secret() -> bytes:
    extra = os.getenv("OTP_HASH_SECRET", "").encode("utf-8")
    return b"otp-hybrid-v1|" + extra


def generate_otp_code() -> str:
    return str(secrets.randbelow(10**OTP_DIGITS)).zfill(OTP_DIGITS)


def hash_otp(*, otp_id: int, code: str) -> str:
    raw = f"{otp_id}:{code}".encode("utf-8")
    digest = hmac.new(_otp_secret(), raw, hashlib.sha256).hexdigest()
    return digest


def verify_otp(*, otp_id: int, code: str, expected_hash: str) -> bool:
    actual = hash_otp(otp_id=otp_id, code=code)
    return hmac.compare_digest(actual, expected_hash)


def normalize_code(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isdigit())[:OTP_DIGITS]
