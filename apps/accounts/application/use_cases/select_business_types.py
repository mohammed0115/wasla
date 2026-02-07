from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from apps.accounts.domain.onboarding_policies import validate_business_types_selection
from apps.accounts.models import AccountProfile, OnboardingProfile
from apps.accounts.application.use_cases.ensure_onboarding_step import (
    EnsureOnboardingStepCommand,
    EnsureOnboardingStepUseCase,
)
from apps.accounts.services.audit_service import AccountAuditService


@dataclass(frozen=True)
class SelectBusinessTypesCommand:
    user: AbstractBaseUser
    business_types: list[str]
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True)
class SelectBusinessTypesResult:
    business_types: list[str]


class SelectBusinessTypesUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: SelectBusinessTypesCommand) -> SelectBusinessTypesResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")

        business_types = validate_business_types_selection(cmd.business_types)

        profile, _created = AccountProfile.objects.get_or_create(
            user=cmd.user,
            defaults={"full_name": ""},
        )
        profile.business_types = business_types
        profile.save(update_fields=["business_types"])
        EnsureOnboardingStepUseCase.execute(
            EnsureOnboardingStepCommand(user=cmd.user, target_step=OnboardingProfile.STEP_BUSINESS)
        )

        AccountAuditService.record_action(
            user=cmd.user,
            action="onboarding_business_types_selected",
            ip_address=cmd.ip_address,
            user_agent=cmd.user_agent,
            metadata={"business_types": business_types},
        )

        return SelectBusinessTypesResult(business_types=business_types)
