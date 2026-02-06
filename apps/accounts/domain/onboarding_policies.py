from __future__ import annotations

from enum import StrEnum

from apps.accounts.domain.errors import AccountValidationError


class CountryCode(StrEnum):
    SA = "SA"
    AE = "AE"
    OTHER = "OTHER"


class BusinessType(StrEnum):
    FASHION = "fashion"
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    BEAUTY = "beauty"
    FOOD = "food"
    ACCESSORIES = "accessories"
    SERVICES = "services"


COUNTRY_OPTIONS: list[tuple[str, str]] = [
    (CountryCode.SA, "🇸🇦 السعودية"),
    (CountryCode.AE, "🇦🇪 الإمارات"),
    (CountryCode.OTHER, "🌍 أخرى"),
]

BUSINESS_TYPE_OPTIONS: list[tuple[str, str]] = [
    (BusinessType.FASHION, "Fashion"),
    (BusinessType.ELECTRONICS, "Electronics"),
    (BusinessType.FURNITURE, "Furniture"),
    (BusinessType.BEAUTY, "Beauty"),
    (BusinessType.FOOD, "Food"),
    (BusinessType.ACCESSORIES, "Accessories"),
    (BusinessType.SERVICES, "Services"),
]


def validate_country_choice(raw: str) -> str:
    value = (raw or "").strip().upper()
    allowed = {c.value for c in CountryCode}
    if value not in allowed:
        raise AccountValidationError("Country selection is required.", field="country")
    return value


def validate_business_types_selection(raw: list[str]) -> list[str]:
    values = [str(v).strip().lower() for v in (raw or []) if str(v).strip()]
    unique: list[str] = []
    for v in values:
        if v not in unique:
            unique.append(v)

    allowed = {b.value for b in BusinessType}
    invalid = [v for v in unique if v not in allowed]
    if invalid:
        raise AccountValidationError("Invalid business type selection.", field="business_types")
    if len(unique) < 1:
        raise AccountValidationError("Select at least one business type.", field="business_types")
    if len(unique) > 5:
        raise AccountValidationError("Select up to 5 business types.", field="business_types")
    return unique

