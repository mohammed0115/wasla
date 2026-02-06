from __future__ import annotations

from enum import StrEnum


class MerchantAuthNextStep(StrEnum):
    OTP_VERIFY = "otp_verify"
    ONBOARDING = "onboarding"
    DASHBOARD = "dashboard"


class MerchantAuthStateMachine:
    """
    Scenario 1 state machine (Register/Login).

    Notes:
    - OTP is optional (Phase 2). For now, `otp_required=False` in all flows.
    - "Onboarding" will be expanded in Scenario 2+ (country/business/store setup).
    """

    @staticmethod
    def next_step_after_register(*, otp_required: bool) -> MerchantAuthNextStep:
        return MerchantAuthNextStep.OTP_VERIFY if otp_required else MerchantAuthNextStep.ONBOARDING

    @staticmethod
    def next_step_after_login(*, otp_required: bool, has_store: bool) -> MerchantAuthNextStep:
        if otp_required:
            return MerchantAuthNextStep.OTP_VERIFY
        return MerchantAuthNextStep.DASHBOARD if has_store else MerchantAuthNextStep.ONBOARDING

