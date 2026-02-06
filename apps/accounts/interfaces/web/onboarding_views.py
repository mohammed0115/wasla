from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.application.use_cases.select_business_types import (
    SelectBusinessTypesCommand,
    SelectBusinessTypesUseCase,
)
from apps.accounts.application.use_cases.select_country import SelectCountryCommand, SelectCountryUseCase
from apps.accounts.domain.errors import AccountValidationError
from apps.accounts.domain.onboarding_policies import BUSINESS_TYPE_OPTIONS, COUNTRY_OPTIONS
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.accounts.models import AccountProfile


def _client_ip(request: HttpRequest) -> str | None:
    value = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
    if not value:
        return None
    return value.split(",")[0].strip() or None


def _next_step_url(step: MerchantNextStep) -> str:
    if step == MerchantNextStep.DASHBOARD:
        return reverse("web:dashboard")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business_types")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("web:dashboard_setup_store")
    return reverse("onboarding:country")


@login_required
def start(request: HttpRequest) -> HttpResponse:
    step = ResolveMerchantNextStepUseCase.execute(ResolveMerchantNextStepCommand(user=request.user)).step
    return redirect(_next_step_url(step))


@login_required
@require_http_methods(["GET", "POST"])
def country(request: HttpRequest) -> HttpResponse:
    profile = AccountProfile.objects.filter(user=request.user).first()
    current_country = (profile.country if profile else "") or ""

    if request.method == "POST":
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            SelectCountryUseCase.execute(
                SelectCountryCommand(
                    user=request.user,
                    country=request.POST.get("country", ""),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountValidationError as exc:
            messages.error(request, str(exc))
        else:
            return redirect("onboarding:business_types")

    return render(
        request,
        "onboarding/country.html",
        {"options": COUNTRY_OPTIONS, "current_country": current_country},
    )


@login_required
@require_http_methods(["GET", "POST"])
def business_types(request: HttpRequest) -> HttpResponse:
    profile = AccountProfile.objects.filter(user=request.user).first()
    selected = list(profile.business_types) if profile and profile.business_types else []

    if request.method == "POST":
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            result = SelectBusinessTypesUseCase.execute(
                SelectBusinessTypesCommand(
                    user=request.user,
                    business_types=request.POST.getlist("business_types"),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountValidationError as exc:
            messages.error(request, str(exc))
        else:
            selected = result.business_types
            return redirect("web:dashboard_setup_store")

    return render(
        request,
        "onboarding/business_types.html",
        {"options": BUSINESS_TYPE_OPTIONS, "selected": selected, "min": 1, "max": 5},
    )

