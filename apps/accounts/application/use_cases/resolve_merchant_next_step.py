from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser

from apps.accounts.domain.post_auth_state_machine import MerchantNextStep, MerchantPostAuthStateMachine
from apps.accounts.models import AccountProfile
from apps.tenants.models import StoreProfile, TenantMembership


@dataclass(frozen=True)
class ResolveMerchantNextStepCommand:
    user: AbstractBaseUser
    otp_required: bool = False


@dataclass(frozen=True)
class ResolveMerchantNextStepResult:
    step: MerchantNextStep


class ResolveMerchantNextStepUseCase:
    @staticmethod
    def execute(cmd: ResolveMerchantNextStepCommand) -> ResolveMerchantNextStepResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")

        has_store = (
            TenantMembership.objects.filter(
                user=cmd.user,
                role=TenantMembership.ROLE_OWNER,
                is_active=True,
                tenant__is_active=True,
            ).exists()
            or StoreProfile.objects.filter(owner=cmd.user, tenant__is_active=True).exists()
        )
        profile = AccountProfile.objects.filter(user=cmd.user).first()
        country_selected = bool(profile and (profile.country or "").strip())
        business_types_selected = bool(profile and (profile.business_types or []))

        step = MerchantPostAuthStateMachine.resolve(
            otp_required=bool(cmd.otp_required),
            has_store=has_store,
            country_selected=country_selected,
            business_types_selected=business_types_selected,
        )
        return ResolveMerchantNextStepResult(step=step)

