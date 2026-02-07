from __future__ import annotations

from enum import StrEnum


class AuthMethod(StrEnum):
    OTP = "otp"
    PASSWORD = "password"
    SOCIAL = "social"


class AuthIdentifierType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    UNKNOWN = "unknown"


class SocialProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
