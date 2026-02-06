from __future__ import annotations

import re

from .errors import EmailInvalidError, FullNameInvalidError, PhoneInvalidError, TermsNotAcceptedError

_PHONE_RE = re.compile(r"^\+?[0-9]{8,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_full_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise FullNameInvalidError("Full name is required.", field="full_name")
    if len(name) > 200:
        raise FullNameInvalidError("Full name must be 200 characters or fewer.", field="full_name")
    return name


def normalize_phone(raw: str) -> str:
    phone = (raw or "").strip()
    phone = re.sub(r"[\s\-()]+", "", phone)
    if phone.startswith("00"):
        phone = f"+{phone[2:]}"
    return phone


def validate_phone(raw: str) -> str:
    phone = normalize_phone(raw)
    if not phone:
        raise PhoneInvalidError("Phone number is required.", field="phone")
    if len(phone) > 32:
        raise PhoneInvalidError("Phone number is too long.", field="phone")
    if not _PHONE_RE.match(phone):
        raise PhoneInvalidError("Phone must contain digits and may start with '+'.", field="phone")
    return phone


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def validate_email(raw: str) -> str:
    email = normalize_email(raw)
    if not email:
        raise EmailInvalidError("Email is required.", field="email")
    if len(email) > 254:
        raise EmailInvalidError("Email must be 254 characters or fewer.", field="email")
    if not _EMAIL_RE.match(email):
        raise EmailInvalidError("Enter a valid email address.", field="email")
    return email


def ensure_terms_accepted(accept_terms: bool) -> None:
    if not accept_terms:
        raise TermsNotAcceptedError("You must accept the terms to continue.", field="accept_terms")
