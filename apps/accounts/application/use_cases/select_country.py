from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from apps.accounts.domain.onboarding_policies import validate_country_choice
from apps.accounts.models import AccountProfile, OnboardingProfile
from apps.accounts.application.use_cases.ensure_onboarding_step import (
    EnsureOnboardingStepCommand,
    EnsureOnboardingStepUseCase,
)
from apps.accounts.services.audit_service import AccountAuditService
from apps.analytics.application.telemetry import TelemetryService, actor_from_user


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
            defaults={"full_name": ""},
        )
        profile.country = country
        profile.save(update_fields=["country"])
        EnsureOnboardingStepUseCase.execute(
            EnsureOnboardingStepCommand(user=cmd.user, target_step=OnboardingProfile.STEP_COUNTRY)
        )

        AccountAuditService.record_action(
            user=cmd.user,
            action="onboarding_country_selected",
            ip_address=cmd.ip_address,
            user_agent=cmd.user_agent,
            metadata={"country": country},
        )
        TelemetryService.track(
            event_name="onboarding.step_completed",
            tenant_ctx=None,
            actor_ctx=actor_from_user(user=cmd.user, actor_type="MERCHANT"),
            properties={"step": "country"},
        )

        return SelectCountryResult(country=country)
