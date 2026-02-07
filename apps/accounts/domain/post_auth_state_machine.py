from __future__ import annotations

from enum import StrEnum

from apps.accounts.domain.onboarding_state_machine import MerchantOnboardingStateMachine, OnboardingStep


class MerchantNextStep(StrEnum):
    COMPLETE_PROFILE = "complete_profile"
    OTP_VERIFY = "otp_verify"
    DASHBOARD = "dashboard"
    ONBOARDING_COUNTRY = "onboarding_country"
    ONBOARDING_BUSINESS_TYPES = "onboarding_business_types"
    STORE_CREATE = "store_create"


class MerchantPostAuthStateMachine:
    @staticmethod
    def resolve(
        *,
        profile_complete: bool,
        otp_required: bool,
        has_store: bool,
        country_selected: bool,
        business_types_selected: bool,
    ) -> MerchantNextStep:
        if not profile_complete:
            return MerchantNextStep.COMPLETE_PROFILE
        if otp_required:
            return MerchantNextStep.OTP_VERIFY
        step = MerchantOnboardingStateMachine.resolve_next_step(
            has_store=has_store,
            country_selected=country_selected,
            business_types_selected=business_types_selected,
        )
        if step == OnboardingStep.DONE:
            return MerchantNextStep.DASHBOARD
        if step == OnboardingStep.COUNTRY:
            return MerchantNextStep.ONBOARDING_COUNTRY
        if step == OnboardingStep.BUSINESS_TYPES:
            return MerchantNextStep.ONBOARDING_BUSINESS_TYPES
        return MerchantNextStep.STORE_CREATE
