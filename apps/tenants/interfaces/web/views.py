from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.application.use_cases.resolve_merchant_next_step import (
    ResolveMerchantNextStepCommand,
    ResolveMerchantNextStepUseCase,
)
from apps.accounts.domain.post_auth_state_machine import MerchantNextStep
from apps.tenants.application.policies.ownership import EnsureTenantOwnershipPolicy
from apps.tenants.application.use_cases.create_store import CreateStoreCommand, CreateStoreUseCase
from apps.tenants.application.use_cases.activate_store import (
    ActivateStoreCommand,
    ActivateStoreUseCase,
    DeactivateStoreCommand,
    DeactivateStoreUseCase,
)
from apps.tenants.application.use_cases.get_store_readiness import (
    GetStoreReadinessCommand,
    GetStoreReadinessUseCase,
)
from apps.tenants.application.use_cases.store_setup_wizard import StoreSetupWizardUseCase
from apps.tenants.application.use_cases.update_payment_settings import (
    UpdatePaymentSettingsCommand,
    UpdatePaymentSettingsUseCase,
)
from apps.tenants.application.use_cases.update_shipping_settings import (
    UpdateShippingSettingsCommand,
    UpdateShippingSettingsUseCase,
)
from apps.tenants.application.use_cases.update_store_settings import (
    UpdateStoreSettingsCommand,
    UpdateStoreSettingsUseCase,
)
from apps.tenants.domain.errors import (
    StoreAccessDeniedError,
    StoreNotReadyError,
    StoreSlugAlreadyTakenError,
)
from apps.tenants.interfaces.web.decorators import resolve_tenant_for_request, tenant_access_required
from apps.tenants.models import StorePaymentSettings, StoreProfile, StoreShippingSettings

from .forms import (
    PaymentSettingsForm,
    ShippingSettingsForm,
    StoreInfoSetupForm,
    StoreSettingsForm,
)


@login_required
@require_http_methods(["GET", "POST"])
def dashboard_setup_store(request: HttpRequest) -> HttpResponse:
    existing = resolve_tenant_for_request(request)
    if existing:
        profile = StoreProfile.objects.filter(tenant=existing).first()
        if profile:
            state = StoreSetupWizardUseCase.get_state(profile=profile)
            if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_PAYMENT:
                return redirect("web:dashboard_setup_payment")
            if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_SHIPPING:
                return redirect("web:dashboard_setup_shipping")
            if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_FIRST_PRODUCT:
                return redirect("web:dashboard_setup_activate")
        return redirect("web:dashboard")

    next_step = ResolveMerchantNextStepUseCase.execute(
        ResolveMerchantNextStepCommand(user=request.user)
    ).step
    if next_step == MerchantNextStep.ONBOARDING_COUNTRY:
        return redirect("onboarding:country")
    if next_step == MerchantNextStep.ONBOARDING_BUSINESS_TYPES:
        return redirect("onboarding:business_types")

    form = StoreInfoSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = CreateStoreUseCase.execute(
                CreateStoreCommand(
                    user=request.user,
                    name=form.cleaned_data["name"],
                    slug=form.cleaned_data["slug"],
                    currency=form.cleaned_data.get("currency") or "SAR",
                    language=form.cleaned_data.get("language") or "ar",
                )
            )
        except StoreSlugAlreadyTakenError as exc:
            form.add_error("slug", str(exc))
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            request.session["store_id"] = result.tenant.id
            request.tenant = result.tenant
            if result.created:
                messages.success(request, "Store created successfully.")
            else:
                messages.info(request, "You already have a store. Redirected to your dashboard.")
            profile = StoreProfile.objects.filter(tenant=result.tenant).first()
            if profile:
                state = StoreSetupWizardUseCase.get_state(profile=profile)
                if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_PAYMENT:
                    return redirect("web:dashboard_setup_payment")
                if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_SHIPPING:
                    return redirect("web:dashboard_setup_shipping")
                if (
                    not profile.is_setup_complete
                    and state.current_step == StoreSetupWizardUseCase.STEP_FIRST_PRODUCT
                ):
                    return redirect("web:dashboard_setup_activate")
            return redirect("web:dashboard_setup_payment")

    return render(request, "web/store/store_info_setup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def store_create(request: HttpRequest) -> HttpResponse:
    return dashboard_setup_store(request)


@login_required
@tenant_access_required
@require_GET
def store_setup_start(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    profile = StoreProfile.objects.filter(tenant=tenant).first()
    if not profile:
        return redirect("web:dashboard_setup_store")

    state = StoreSetupWizardUseCase.get_state(profile=profile)
    if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_STORE_INFO:
        return redirect("web:dashboard_setup_store")
    if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_PAYMENT:
        return redirect("web:dashboard_setup_payment")
    if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_SHIPPING:
        return redirect("web:dashboard_setup_shipping")
    if not profile.is_setup_complete and state.current_step == StoreSetupWizardUseCase.STEP_FIRST_PRODUCT:
        return redirect("web:dashboard_setup_activate")
    return redirect("web:dashboard")


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def dashboard_setup_payment(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    try:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=request.user, tenant=tenant)
    except StoreAccessDeniedError as exc:
        raise PermissionDenied(str(exc)) from exc

    profile = StoreProfile.objects.filter(tenant=tenant).first()
    if not profile:
        return redirect("web:dashboard_setup_store")

    state = StoreSetupWizardUseCase.get_state(profile=profile)
    if not profile.is_setup_complete and state.current_step < StoreSetupWizardUseCase.STEP_PAYMENT:
        return redirect("web:dashboard_setup_store")

    existing = StorePaymentSettings.objects.filter(tenant=tenant).first()
    initial = None
    if existing:
        initial = {
            "payment_mode": existing.mode,
            "provider_name": existing.provider_name,
            "merchant_key": existing.merchant_key,
            "webhook_secret": existing.webhook_secret,
            "is_enabled": existing.is_enabled,
        }

    form = PaymentSettingsForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            UpdatePaymentSettingsUseCase.execute(
                UpdatePaymentSettingsCommand(
                    user=request.user,
                    tenant=tenant,
                    payment_mode=form.cleaned_data["payment_mode"],
                    provider_name=form.cleaned_data.get("provider_name") or "",
                    merchant_key=form.cleaned_data.get("merchant_key") or "",
                    webhook_secret=form.cleaned_data.get("webhook_secret") or "",
                    is_enabled=form.cleaned_data.get("is_enabled", False),
                )
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Payment settings saved.")
            return redirect("web:dashboard_setup_shipping")

    return render(
        request,
        "web/store/setup_payment.html",
        {"form": form, "tenant": tenant, "step": 2, "state": state},
    )


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def dashboard_setup_shipping(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    try:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=request.user, tenant=tenant)
    except StoreAccessDeniedError as exc:
        raise PermissionDenied(str(exc)) from exc

    profile = StoreProfile.objects.filter(tenant=tenant).first()
    if not profile:
        return redirect("web:dashboard_setup_store")

    state = StoreSetupWizardUseCase.get_state(profile=profile)
    if not profile.is_setup_complete and state.current_step < StoreSetupWizardUseCase.STEP_SHIPPING:
        return redirect("web:dashboard_setup_payment")

    existing = StoreShippingSettings.objects.filter(tenant=tenant).first()
    initial = None
    if existing:
        initial = {
            "fulfillment_mode": existing.fulfillment_mode,
            "origin_city": existing.origin_city,
            "delivery_fee_flat": existing.delivery_fee_flat,
            "free_shipping_threshold": existing.free_shipping_threshold,
            "is_enabled": existing.is_enabled,
        }

    form = ShippingSettingsForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            UpdateShippingSettingsUseCase.execute(
                UpdateShippingSettingsCommand(
                    user=request.user,
                    tenant=tenant,
                    fulfillment_mode=form.cleaned_data["fulfillment_mode"],
                    origin_city=form.cleaned_data.get("origin_city") or "",
                    delivery_fee_flat=form.cleaned_data.get("delivery_fee_flat"),
                    free_shipping_threshold=form.cleaned_data.get("free_shipping_threshold"),
                    is_enabled=form.cleaned_data.get("is_enabled", False),
                )
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("web:dashboard_setup_payment")
        else:
            messages.success(request, "Shipping settings saved. Next: activate your store.")
            return redirect("web:dashboard_setup_activate")

    return render(
        request,
        "web/store/setup_shipping.html",
        {"form": form, "tenant": tenant, "step": 3, "state": state},
    )


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def dashboard_setup_activate(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    try:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=request.user, tenant=tenant)
    except StoreAccessDeniedError as exc:
        raise PermissionDenied(str(exc)) from exc

    profile = StoreProfile.objects.filter(tenant=tenant).first()
    if not profile:
        return redirect("web:dashboard_setup_store")

    state = StoreSetupWizardUseCase.get_state(profile=profile)
    if not profile.is_setup_complete and state.current_step < StoreSetupWizardUseCase.STEP_FIRST_PRODUCT:
        if state.current_step == StoreSetupWizardUseCase.STEP_STORE_INFO:
            return redirect("web:dashboard_setup_store")
        if state.current_step == StoreSetupWizardUseCase.STEP_PAYMENT:
            return redirect("web:dashboard_setup_payment")
        if state.current_step == StoreSetupWizardUseCase.STEP_SHIPPING:
            return redirect("web:dashboard_setup_shipping")

    readiness = GetStoreReadinessUseCase.execute(
        GetStoreReadinessCommand(user=request.user, tenant=tenant)
    )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "activate":
            try:
                ActivateStoreUseCase.execute(ActivateStoreCommand(user=request.user, tenant=tenant))
            except StoreNotReadyError as exc:
                reasons = exc.reasons or [str(exc)]
                for reason in reasons:
                    messages.error(request, reason)
            else:
                messages.success(request, "Store activated successfully. Your store is now live.")
                return redirect("web:dashboard_setup_activate")
        elif action == "deactivate":
            DeactivateStoreUseCase.execute(
                DeactivateStoreCommand(user=request.user, tenant=tenant, reason=request.POST.get("reason") or "")
            )
            messages.success(request, "Store deactivated. Visitors will see a maintenance page.")
            return redirect("web:dashboard_setup_activate")
        else:
            messages.error(request, "Invalid action.")
            return redirect("web:dashboard_setup_activate")

    public_domain = (tenant.domain or "").strip()
    if public_domain:
        public_url_hint = f"{public_domain}"
    else:
        public_url_hint = f"{tenant.slug}.<your-domain>"

    return render(
        request,
        "web/store/setup_activate.html",
        {
            "tenant": tenant,
            "profile": profile,
            "state": state,
            "step": 4,
            "readiness": readiness,
            "public_url_hint": public_url_hint,
            "storefront_path": "/store/",
        },
    )


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def store_setup_step1(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    try:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=request.user, tenant=tenant)
    except StoreAccessDeniedError as exc:
        raise PermissionDenied(str(exc)) from exc

    initial = {
        "name": tenant.name,
        "slug": tenant.slug,
        "currency": tenant.currency,
        "language": tenant.language,
        "primary_color": tenant.primary_color,
        "secondary_color": tenant.secondary_color,
    }
    form = StoreSettingsForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            UpdateStoreSettingsUseCase.execute(
                UpdateStoreSettingsCommand(
                    user=request.user,
                    tenant=tenant,
                    name=form.cleaned_data["name"],
                    slug=form.cleaned_data["slug"],
                    currency=form.cleaned_data.get("currency") or "SAR",
                    language=form.cleaned_data.get("language") or "ar",
                    logo_file=form.cleaned_data.get("logo"),
                    primary_color=form.cleaned_data.get("primary_color") or "",
                    secondary_color=form.cleaned_data.get("secondary_color") or "",
                )
            )
        except StoreSlugAlreadyTakenError as exc:
            form.add_error("slug", str(exc))
        else:
            messages.success(request, "Store info saved.")
            return redirect("web:dashboard_setup_payment")

    context = {"form": form, "tenant": tenant, "step": 1}
    return render(request, "web/store/setup_step1.html", context)


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def store_setup_step2(request: HttpRequest) -> HttpResponse:
    return redirect("web:dashboard_setup_payment")


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def store_setup_step3(request: HttpRequest) -> HttpResponse:
    return redirect("web:dashboard_setup_shipping")


@login_required
@tenant_access_required
@require_http_methods(["GET", "POST"])
def store_setup_step4(request: HttpRequest) -> HttpResponse:
    return redirect("web:dashboard_setup_activate")


@login_required
@tenant_access_required
@require_POST
def store_settings_update(request: HttpRequest) -> HttpResponse:
    tenant = request.tenant
    try:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=request.user, tenant=tenant)
    except StoreAccessDeniedError as exc:
        raise PermissionDenied(str(exc)) from exc
    form = StoreSettingsForm(request.POST, request.FILES or None)
    if not form.is_valid():
        messages.error(request, "Invalid store settings.")
        return redirect("web:settings")

    try:
        UpdateStoreSettingsUseCase.execute(
            UpdateStoreSettingsCommand(
                user=request.user,
                tenant=tenant,
                name=form.cleaned_data["name"],
                slug=form.cleaned_data["slug"],
                currency=form.cleaned_data.get("currency") or "SAR",
                language=form.cleaned_data.get("language") or "ar",
                logo_file=form.cleaned_data.get("logo"),
                primary_color=form.cleaned_data.get("primary_color") or "",
                secondary_color=form.cleaned_data.get("secondary_color") or "",
            )
        )
    except StoreSlugAlreadyTakenError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Store settings updated.")

    return redirect("web:settings")
