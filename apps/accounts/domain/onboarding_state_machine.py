from __future__ import annotations

from enum import StrEnum


class OnboardingStep(StrEnum):
    COUNTRY = "country"
    BUSINESS_TYPES = "business_types"
    STORE = "store"
    DONE = "done"


class MerchantOnboardingStateMachine:
    @staticmethod
    def resolve_next_step(
        *,
        has_store: bool,
        country_selected: bool,
        business_types_selected: bool,
    ) -> OnboardingStep:
        if has_store:
            return OnboardingStep.DONE
        if not country_selected:
            return OnboardingStep.COUNTRY
        if not business_types_selected:
            return OnboardingStep.BUSINESS_TYPES
        return OnboardingStep.STORE

