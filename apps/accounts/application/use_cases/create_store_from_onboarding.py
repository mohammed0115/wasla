from __future__ import annotations

"""
Create a store (tenant) from onboarding.

AR:
- يتحقق من خطوة الـ onboarding الحالية.
- يمنع إنشاء أكثر من متجر لنفس الـ Owner.
- ينشئ Tenant + StoreProfile + TenantMembership بشكل ذري (atomic).

EN:
- Validates the current onboarding step.
- Prevents creating multiple stores for the same owner.
- Creates Tenant + StoreProfile + TenantMembership atomically.
"""

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from apps.accounts.domain.errors import AccountValidationError
from apps.accounts.domain.hybrid_policies import validate_store_slug
from apps.accounts.application.use_cases.ensure_onboarding_step import (
    EnsureOnboardingStepCommand,
    EnsureOnboardingStepUseCase,
)
from apps.accounts.models import OnboardingProfile
from apps.tenants.models import StoreProfile, Tenant, TenantMembership


@dataclass(frozen=True)
class CreateStoreFromOnboardingCommand:
    """Input payload for creating a tenant store during onboarding."""

    user: AbstractBaseUser
    name: str
    slug: str


@dataclass(frozen=True)
class CreateStoreFromOnboardingResult:
    """Return value for a successful store creation."""

    tenant_id: int
    slug: str


class CreateStoreFromOnboardingUseCase:
    """Orchestrates tenant + store profile creation as part of onboarding."""

    @staticmethod
    @transaction.atomic
    def execute(cmd: CreateStoreFromOnboardingCommand) -> CreateStoreFromOnboardingResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise AccountValidationError("Authentication required.")

        profile = OnboardingProfile.objects.select_for_update().filter(user=cmd.user).first()
        if not profile:
            raise AccountValidationError("Onboarding not started.")
        if profile.step not in (OnboardingProfile.STEP_BUSINESS, OnboardingProfile.STEP_STORE):
            raise AccountValidationError("Complete onboarding steps first.")

        # AR: تمنع أكثر من متجر Owner لنفس المستخدم (سواء عبر StoreProfile أو Membership).
        # EN: Prevent the user from owning multiple stores (via profile or membership).
        if StoreProfile.objects.filter(owner=cmd.user).exists() or TenantMembership.objects.filter(
            user=cmd.user, role=TenantMembership.ROLE_OWNER, is_active=True
        ).exists():
            raise AccountValidationError("User already owns a store.")

        slug = validate_store_slug(cmd.slug)
        if Tenant.objects.filter(slug=slug).exists():
            raise AccountValidationError("Store slug already exists.", field="slug")

        name = (cmd.name or "").strip()
        if not name:
            raise AccountValidationError("Store name is required.", field="name")

        EnsureOnboardingStepUseCase.execute(
            EnsureOnboardingStepCommand(user=cmd.user, target_step=OnboardingProfile.STEP_STORE)
        )

        tenant = Tenant.objects.create(
            slug=slug,
            name=name,
            is_active=True,
            currency="SAR",
            language="ar",
        )
        StoreProfile.objects.create(
            tenant=tenant,
            owner=cmd.user,
            store_info_completed=True,
            setup_step=1,
            is_setup_complete=True,
        )
        TenantMembership.objects.create(tenant=tenant, user=cmd.user, role=TenantMembership.ROLE_OWNER, is_active=True)

        profile.step = OnboardingProfile.STEP_DONE
        profile.save(update_fields=["step"])

        return CreateStoreFromOnboardingResult(tenant_id=tenant.id, slug=tenant.slug)
