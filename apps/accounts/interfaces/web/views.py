from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.application.use_cases.login import LoginCommand, LoginUseCase
from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.application.use_cases.register_merchant import (
    RegisterMerchantCommand,
    RegisterMerchantUseCase,
)
from apps.accounts.domain.errors import (
    AccountAlreadyExistsError,
    AccountValidationError,
    InvalidCredentialsError,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.accounts.interfaces.web.forms import MerchantLoginForm, MerchantSignupForm


def _client_ip(request: HttpRequest) -> str | None:
    value = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
    if not value:
        return None
    return value.split(",")[0].strip() or None


def _login_user(request: HttpRequest, user: object) -> None:
    backend = getattr(user, "backend", "") or (settings.AUTHENTICATION_BACKENDS[0] if settings.AUTHENTICATION_BACKENDS else "")
    if backend:
        login(request, user, backend=backend)
        return
    login(request, user)


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


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    signup_form = MerchantSignupForm()
    form = MerchantLoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            result = LoginUseCase.execute(
                LoginCommand(
                    identifier=form.cleaned_data["identifier"],
                    password=form.cleaned_data["password"],
                )
            )
        except InvalidCredentialsError as exc:
            form.add_error(None, str(exc))
        else:
            _login_user(request, result.user)
            messages.success(request, "Logged in successfully.")
            step = ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=result.otp_required)
            ).step
            if step == MerchantNextStep.DASHBOARD:
                next_url = request.POST.get("next") or request.GET.get("next") or reverse("web:dashboard")
                return redirect(next_url)
            return redirect(_next_step_url(step))

    return render(
        request,
        "registration/auth.html",
        {"active_tab": "login", "login_form": form, "signup_form": signup_form},
    )


@require_http_methods(["GET", "POST"])
def signup_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    login_form = MerchantLoginForm()
    form = MerchantSignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        try:
            result = RegisterMerchantUseCase.execute(
                RegisterMerchantCommand(
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    accept_terms=bool(form.cleaned_data["accept_terms"]),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
        except AccountAlreadyExistsError as exc:
            form.add_error(getattr(exc, "field", None) or None, str(exc))
        except AccountValidationError as exc:
            form.add_error(getattr(exc, "field", None) or None, str(exc))
        else:
            _login_user(request, result.user)
            messages.success(request, "Account created successfully.")
            step = ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=result.otp_required)
            ).step
            return redirect(_next_step_url(step))

    return render(
        request,
        "registration/auth.html",
        {"active_tab": "register", "login_form": login_form, "signup_form": form},
    )


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")
