from __future__ import annotations

import re

from .errors import StoreNameInvalidError, StoreSlugInvalidError, StoreSlugReservedError

RESERVED_TENANT_SLUGS: set[str] = {
    "admin",
    "api",
    "www",
    "dashboard",
    "store",
}

_SUBDOMAIN_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$")
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$"
)


def validate_store_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise StoreNameInvalidError("Store name is required.")
    if len(name) > 200:
        raise StoreNameInvalidError("Store name must be 200 characters or fewer.")
    return name


def normalize_tenant_slug(raw: str) -> str:
    return (raw or "").strip().lower()


def normalize_slug(raw: str) -> str:
    return normalize_tenant_slug(raw)


def validate_tenant_slug(raw: str) -> str:
    slug = normalize_tenant_slug(raw)
    if not slug:
        raise StoreSlugInvalidError("Store slug is required.")
    if slug in RESERVED_TENANT_SLUGS:
        raise StoreSlugReservedError("This store slug is reserved.")
    if len(slug) > 63:
        raise StoreSlugInvalidError("Store slug must be 63 characters or fewer.")
    if not _SUBDOMAIN_SLUG_RE.match(slug):
        raise StoreSlugInvalidError(
            "Store slug must be a valid subdomain label (letters/numbers/hyphens, no leading/trailing hyphen)."
        )
    return slug


def normalize_hex_color(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if not value.startswith("#"):
        value = f"#{value}"
    return value.lower()


def validate_hex_color(raw: str) -> str:
    value = normalize_hex_color(raw)
    if not value:
        return ""
    if not _HEX_COLOR_RE.match(value):
        raise StoreSlugInvalidError("Brand color must be a valid hex color like #1d4ed8.")
    return value


def normalize_custom_domain(raw: str) -> str:
    return (raw or "").strip().lower()


def validate_custom_domain(raw: str) -> str:
    domain = normalize_custom_domain(raw)
    if not domain:
        return ""
    if "://" in domain or "/" in domain or " " in domain:
        raise StoreSlugInvalidError("Custom domain must be a hostname only (no scheme/path/spaces).")
    if not _DOMAIN_RE.match(domain):
        raise StoreSlugInvalidError("Custom domain must be a valid hostname like example.com.")
    return domain
