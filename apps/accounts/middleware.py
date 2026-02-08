from __future__ import annotations

"""
Onboarding redirect middleware.

AR:
- يضمن أن التاجر لا يصل للـ dashboard قبل إكمال خطوات onboarding المطلوبة.
- يستثني المسارات العامة مثل: `/auth/`, `/onboarding/`, `/admin/`, `/static/`, `/media/`.

EN:
- Ensures a merchant cannot access the dashboard before completing required onboarding steps.
- Exempts public paths like: `/auth/`, `/onboarding/`, `/admin/`, `/static/`, `/media/`.
"""

from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep


class OnboardingRedirectMiddleware:
    """Redirect authenticated users to the next onboarding step when needed."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith("/api/"):
            allowed = (
                request.path.startswith("/auth/")
                or request.path.startswith("/onboarding/")
                or request.path.startswith("/dashboard/setup/")
                or request.path.startswith("/store/setup/")
                or request.path.startswith("/store/create/")
                or request.path.startswith("/admin/")
                or request.path.startswith("/static/")
                or request.path.startswith("/media/")
            )
            if not allowed:
                step = ResolveMerchantNextStepUseCase.execute(
                    ResolveMerchantNextStepCommand(user=request.user, otp_required=False)
                ).step
                if step != MerchantNextStep.DASHBOARD:
                    return redirect(_next_step_url(step))

        return self.get_response(request)


def _next_step_url(step: MerchantNextStep) -> str:
    if step == MerchantNextStep.COMPLETE_PROFILE:
        return reverse("auth:complete_profile")
    if step == MerchantNextStep.OTP_VERIFY:
        return reverse("auth:otp_verify")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("web:dashboard_setup_store")
    return reverse("web:dashboard")
