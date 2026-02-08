from __future__ import annotations

"""
Ensure onboarding step.

AR: Use case لضبط خطوة الـ onboarding الحالية للمستخدم (مع التحقق من ترتيب الخطوات).
EN: Use case to set/update the user's current onboarding step (with step-order validation).
"""

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser

from apps.accounts.domain.hybrid_policies import validate_onboarding_step_order
from apps.accounts.models import OnboardingProfile


@dataclass(frozen=True)
class EnsureOnboardingStepCommand:
    """Command to move a user onboarding profile to a target step."""

    user: AbstractBaseUser
    target_step: str


@dataclass(frozen=True)
class EnsureOnboardingStepResult:
    """Result after ensuring the onboarding step."""

    step: str


class EnsureOnboardingStepUseCase:
    @staticmethod
    def execute(cmd: EnsureOnboardingStepCommand) -> EnsureOnboardingStepResult:
        if not getattr(cmd.user, "is_authenticated", False):
            raise ValueError("Authentication required.")

        profile, _ = OnboardingProfile.objects.get_or_create(user=cmd.user)
        validate_onboarding_step_order(current_step=profile.step, target_step=cmd.target_step)
        if profile.step != cmd.target_step:
            profile.step = cmd.target_step
            profile.save(update_fields=["step"])
        return EnsureOnboardingStepResult(step=profile.step)
