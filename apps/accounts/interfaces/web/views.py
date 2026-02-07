from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from urllib.parse import urlencode
from apps.sms.domain.errors import SmsError

from apps.accounts.application.use_cases.complete_profile import (
    CompleteMerchantProfileCommand,
    CompleteMerchantProfileUseCase,
)
from apps.accounts.application.use_cases.login import LoginCommand, LoginUseCase
from apps.accounts.application.use_cases.request_hybrid_otp import (
    RequestHybridOtpCommand,
    RequestHybridOtpUseCase,
)
from apps.accounts.application.use_cases.resolve_auth_entry import (
    ResolveAuthEntryCommand,
    ResolveAuthEntryUseCase,
)
from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.application.use_cases.register_merchant import (
    RegisterMerchantCommand,
    RegisterMerchantUseCase,
)
from apps.accounts.domain.auth_flow import AuthMethod
from apps.accounts.domain.errors import (
    AccountAlreadyExistsError,
    AccountValidationError,
    InvalidCredentialsError,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.accounts.interfaces.web.forms import (
    AuthStartForm,
    MerchantLoginForm,
    MerchantSignupForm,
    OtpLoginRequestForm,
    OtpLoginVerifyForm,
)
from apps.accounts.application.use_cases.request_email_otp import RequestEmailOtpCommand, RequestEmailOtpUseCase
from apps.accounts.application.use_cases.verify_email_otp import VerifyEmailOtpCommand, VerifyEmailOtpUseCase
from apps.accounts.application.use_cases.verify_hybrid_otp import (
    VerifyHybridOtpCommand,
    VerifyHybridOtpUseCase,
)
from apps.accounts.models import AccountProfile


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
    if step == MerchantNextStep.COMPLETE_PROFILE:
        return reverse("onboarding:country")
    if step == MerchantNextStep.OTP_VERIFY:
        return reverse("auth:otp_verify")
    if step == MerchantNextStep.DASHBOARD:
        return reverse("web:dashboard")
    if step == MerchantNextStep.ONBOARDING_COUNTRY:
        return reverse("onboarding:country")
    if step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return reverse("onboarding:business_types")
    if step == MerchantNextStep.STORE_CREATE:
        return reverse("onboarding:store")
    return reverse("onboarding:country")


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    signup_form = MerchantSignupForm()
    form = MerchantLoginForm(
        request.POST or None,
        initial={"identifier": request.GET.get("identifier", "")},
    )

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
    form = MerchantSignupForm(
        request.POST or None,
        initial={
            "email": request.GET.get("email", ""),
            "phone": request.GET.get("phone", ""),
        },
    )

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


@require_http_methods(["GET", "POST"])
def complete_profile_view(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect(reverse("auth:login"))

    profile = AccountProfile.objects.filter(user=request.user).first()
    form = MerchantSignupForm(
        request.POST or None,
        initial={
            "full_name": (profile.full_name if profile else ""),
            "phone": (profile.phone if profile else ""),
            "email": getattr(request.user, "email", ""),
        },
    )

    if request.method == "POST" and form.is_valid():
        try:
            result = CompleteMerchantProfileUseCase.execute(
                CompleteMerchantProfileCommand(
                    user=request.user,
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    accept_terms=bool(form.cleaned_data["accept_terms"]),
                    ip_address=_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
            )
        except AccountAlreadyExistsError as exc:
            form.add_error(getattr(exc, "field", None) or None, str(exc))
        except AccountValidationError as exc:
            form.add_error(getattr(exc, "field", None) or None, str(exc))
        else:
            messages.success(request, "Profile completed successfully.")
            step = ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=request.user, otp_required=result.otp_required)
            ).step
            return redirect(_next_step_url(step))

    return render(request, "registration/complete_profile.html", {"form": form})


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")


@require_http_methods(["GET", "POST"])
def otp_verify_view(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect(reverse("auth:login"))

    if request.method == "POST":
        action = (request.POST.get("action") or "verify").strip()
        if action == "request":
            try:
                _ = RequestEmailOtpUseCase.execute(RequestEmailOtpCommand(user=request.user))
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "OTP sent to your email.")
            return redirect(reverse("auth:otp_verify"))

        code = (request.POST.get("code") or "").strip()
        try:
            _ = VerifyEmailOtpUseCase.execute(VerifyEmailOtpCommand(user=request.user, code=code))
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Email verified successfully.")
            step = ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=request.user, otp_required=False)
            ).step
            return redirect(_next_step_url(step))

    return render(request, "registration/otp_verify.html", {})


@require_http_methods(["GET", "POST"])
def otp_login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    request_form = OtpLoginRequestForm(request.POST or None)
    verify_form = OtpLoginVerifyForm(request.POST or None)
    identifier = request.session.get("otp_login_identifier", "")

    if request.method == "POST":
        action = (request.POST.get("action") or "request").strip()
        if action == "request" and request_form.is_valid():
            try:
                result = RequestHybridOtpUseCase.execute(
                    RequestHybridOtpCommand(
                        identifier=request_form.cleaned_data["identifier"],
                        ip_address=_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    )
                )
            except (AccountValidationError, SmsError, ValueError) as exc:
                messages.error(request, str(exc))
            else:
                request.session["otp_login_identifier"] = result.identifier
                if result.sent:
                    messages.success(request, "OTP sent successfully.")
                else:
                    messages.info(request, "OTP already sent recently. Please check your inbox.")
            return redirect(reverse("auth:otp_login"))

        if action == "verify" and verify_form.is_valid():
            if not identifier:
                messages.error(request, "Please request an OTP first.")
                return redirect(reverse("auth:otp_login"))
            try:
                result = VerifyHybridOtpUseCase.execute(
                    VerifyHybridOtpCommand(identifier=identifier, code=verify_form.cleaned_data["code"])
                )
            except (AccountValidationError, ValueError) as exc:
                messages.error(request, str(exc))
            else:
                _login_user(request, result.user)
                request.session.pop("otp_login_identifier", None)
                messages.success(request, "Logged in successfully.")
                profile = AccountProfile.objects.filter(user=result.user).first()
                otp_required = bool(
                    profile and profile.email_verified_at is None and (getattr(result.user, "email", "") or "").strip()
                )
                step = ResolveMerchantNextStepUseCase.execute(
                    ResolveMerchantNextStepCommand(user=result.user, otp_required=otp_required)
                ).step
                return redirect(_next_step_url(step))

    return render(
        request,
        "registration/otp_login.html",
        {"request_form": request_form, "verify_form": verify_form, "identifier": identifier},
    )


@require_http_methods(["GET", "POST"])
def auth_start_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    form = AuthStartForm(
        request.POST or None,
        initial={"identifier": request.GET.get("identifier", "")},
    )
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"]
        try:
            result = ResolveAuthEntryUseCase.execute(ResolveAuthEntryCommand(identifier=identifier))
        except AccountValidationError as exc:
            form.add_error(None, str(exc))
        else:
            if result.default_method == AuthMethod.OTP.value:
                try:
                    issued = RequestHybridOtpUseCase.execute(
                        RequestHybridOtpCommand(
                            identifier=identifier,
                            ip_address=_client_ip(request),
                            user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        )
                    )
                except (AccountValidationError, SmsError, ValueError) as exc:
                    messages.error(request, str(exc))
                else:
                    request.session["auth_identifier"] = issued.identifier
                    if issued.sent:
                        messages.success(request, "OTP sent. Please verify to continue.")
                    else:
                        messages.info(request, "OTP already sent recently. Please check your inbox.")
                    return redirect("auth:verify")
            elif result.default_method == AuthMethod.PASSWORD.value:
                query = urlencode({"identifier": result.identifier})
                return redirect(f"{reverse('login')}?{query}")
            else:
                prefill = {}
                if result.identifier_type.value == "email":
                    prefill["email"] = result.identifier
                if result.identifier_type.value == "phone":
                    prefill["phone"] = result.identifier
                query = urlencode(prefill)
                url = reverse("signup")
                return redirect(f"{url}?{query}" if query else url)

    return render(request, "auth/start.html", {"form": form})


@require_http_methods(["GET", "POST"])
def auth_verify_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    identifier = request.session.get("auth_identifier", "")
    if not identifier:
        messages.error(request, "Please start the login flow first.")
        return redirect("auth:start")
    form = OtpLoginVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = VerifyHybridOtpUseCase.execute(
                VerifyHybridOtpCommand(
                    identifier=identifier,
                    code=form.cleaned_data["code"],
                )
            )
        except (AccountValidationError, ValueError) as exc:
            messages.error(request, str(exc))
        else:
            _login_user(request, result.user)
            request.session.pop("auth_identifier", None)
            profile = AccountProfile.objects.filter(user=result.user).first()
            otp_required = bool(
                profile and profile.email_verified_at is None and (getattr(result.user, "email", "") or "").strip()
            )
            step = ResolveMerchantNextStepUseCase.execute(
                ResolveMerchantNextStepCommand(user=result.user, otp_required=otp_required)
            ).step
            return redirect(_next_step_url(step))

    return render(request, "auth/verify.html", {"form": form, "identifier": identifier})
