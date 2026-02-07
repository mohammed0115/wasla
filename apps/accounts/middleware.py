from __future__ import annotations

from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep


class OnboardingRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith("/api/"):
            allowed = (
                request.path.startswith("/auth/")
                or request.path.startswith("/onboarding/")
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
    if step == MerchantNextStep.OTP_VERIFY:
        return reverse("auth:verify")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business_types")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("onboarding:store")
    return reverse("web:dashboard")
