from __future__ import annotations

import re

from django.conf import settings

from apps.accounts.domain.errors import AccountValidationError
from apps.accounts.domain.policies import normalize_email, normalize_phone
from apps.accounts.models import OnboardingProfile

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_RESERVED = {"admin", "api", "www", "dashboard", "store"}
_TEST_OTP_CODE = "12345"


def validate_identifier(raw: str) -> tuple[str, str]:
    value = (raw or "").strip()
    if not value:
        raise AccountValidationError("Identifier is required.", field="identifier")
    if "@" in value:
        return normalize_email(value), "email"
    return normalize_phone(value), "phone"


def validate_store_slug(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        raise AccountValidationError("Store slug is required.", field="slug")
    if len(value) > 60:
        raise AccountValidationError("Store slug is too long.", field="slug")
    if value in _RESERVED:
        raise AccountValidationError("This slug is reserved.", field="slug")
    if not _SLUG_RE.match(value):
        raise AccountValidationError("Slug must be lowercase letters, numbers, and hyphens.", field="slug")
    if value.startswith("-") or value.endswith("-"):
        raise AccountValidationError("Slug cannot start or end with '-'.", field="slug")
    return value


def validate_onboarding_step_order(*, current_step: str, target_step: str) -> None:
    order = [
        OnboardingProfile.STEP_REGISTERED,
        OnboardingProfile.STEP_COUNTRY,
        OnboardingProfile.STEP_BUSINESS,
        OnboardingProfile.STEP_STORE,
        OnboardingProfile.STEP_DONE,
    ]
    try:
        current_index = order.index(current_step)
        target_index = order.index(target_step)
    except ValueError as exc:
        raise AccountValidationError("Invalid onboarding step.") from exc
    if target_index < current_index:
        return
    if target_index - current_index > 1:
        raise AccountValidationError("Onboarding steps must be completed in order.")


def validate_otp_rules(*, recent_count: int, has_active: bool, attempts: int) -> None:
    if recent_count >= 3:
        raise AccountValidationError("Too many OTP requests. Try later.")
    if has_active and attempts >= 5:
        raise AccountValidationError("Too many OTP attempts.")


def test_otp_code() -> str:
    return str(getattr(settings, "TEST_OTP_CODE", _TEST_OTP_CODE) or _TEST_OTP_CODE)


def is_testing_otp_allowed() -> bool:
    env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    if env in {"prod", "production"}:
        return False
    if env in {"test", "staging"}:
        return True
    return bool(getattr(settings, "DEBUG", False))
