from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from apps.accounts.domain.onboarding_policies import validate_country_choice
from apps.accounts.models import AccountProfile
from apps.accounts.services.audit_service import AccountAuditService


@dataclass(frozen=True)
class SelectCountryCommand:
    user: AbstractBaseUser
    country: str
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class SelectCountryResult:
    country: str


class SelectCountryUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: SelectCountryCommand) -> SelectCountryResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")

        country = validate_country_choice(cmd.country)

        profile, _created = AccountProfile.objects.get_or_create(
            user=cmd.user,
            defaults={"phone": getattr(cmd.user, "username", ""), "full_name": ""},
        )
        profile.country = country
        profile.save(update_fields=["country"])

        AccountAuditService.record_action(
            user=cmd.user,
            action="onboarding_country_selected",
            ip_address=cmd.ip_address,
            user_agent=cmd.user_agent,
            metadata={"country": country},
        )

        return SelectCountryResult(country=country)

