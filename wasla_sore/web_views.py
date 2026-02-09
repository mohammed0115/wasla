from __future__ import annotations

from datetime import date
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.models import Category, Inventory, Product
from apps.catalog.services.product_service import ProductService
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.services.order_lifecycle_service import OrderLifecycleService
from apps.orders.services.order_service import OrderService
from apps.payments.models import Payment
from apps.payments.services.payment_service import PaymentService
from apps.plugins.models import InstalledPlugin, Plugin
from apps.plugins.services.installation_service import PluginInstallationService
from apps.reviews.models import Review
from apps.reviews.services.review_service import ReviewService
from apps.shipping.models import Shipment
from apps.shipping.services.shipping_service import ShippingService
from apps.subscriptions.models import SubscriptionPlan
from apps.subscriptions.services.subscription_service import SubscriptionService
from apps.wallet.services.wallet_service import WalletService
from apps.tenants.interfaces.web.decorators import tenant_access_required
from apps.tenants.domain.policies import normalize_domain
from apps.tenants.interfaces.web.forms import CustomDomainForm, StoreSettingsForm
from apps.tenants.models import StoreDomain


def _get_store_id(request: HttpRequest) -> int:
    tenant = getattr(request, "tenant", None)
    tenant_id = getattr(tenant, "id", None) if tenant is not None else None
    if isinstance(tenant_id, int) and tenant_id > 0:
        return tenant_id
    raise PermissionDenied("Tenant context is required.")


class ProductForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=0, label="Stock quantity")

    class Meta:
        model = Product
        fields = ["sku", "name", "price", "image", "categories"]
        widgets = {
            "categories": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, store_id: int | None = None, **kwargs):
        self.store_id = store_id
        super().__init__(*args, **kwargs)
        for field_name in ["sku", "name", "price", "quantity", "image"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.setdefault("class", "form-control")

        if "categories" in self.fields:
            self.fields["categories"].widget.attrs.setdefault("class", "form-check-input")
            resolved_store_id = (
                self.store_id
                if self.store_id is not None
                else getattr(self.instance, "store_id", None)
            )
            if resolved_store_id is not None:
                self.fields["categories"].queryset = (
                    Category.objects.filter(store_id=resolved_store_id).order_by("name")
                )

        if self.instance and self.instance.pk:
            try:
                self.fields["quantity"].initial = self.instance.inventory.quantity
            except Inventory.DoesNotExist:
                self.fields["quantity"].initial = 0


class OrderCreateForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
    )

    def __init__(self, *args, store_id: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if store_id is not None:
            self.fields["customer"].queryset = (
                Customer.objects.filter(store_id=store_id, is_active=True).order_by(
                    "full_name", "email"
                )
            )
        self.fields["customer"].widget.attrs.setdefault("class", "form-select")


class OrderItemForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.IntegerField(min_value=1)
    price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    def __init__(self, *args, store_id: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if store_id is not None:
            self.fields["product"].queryset = (
                Product.objects.filter(store_id=store_id, is_active=True).order_by("name")
            )
        self.fields["product"].widget.attrs.setdefault("class", "form-select")
        self.fields["quantity"].widget.attrs.setdefault("class", "form-control")
        self.fields["price"].widget.attrs.setdefault("class", "form-control")


OrderItemFormSet = forms.formset_factory(OrderItemForm, extra=3, can_delete=True)


class ShipmentCreateForm(forms.Form):
    carrier = forms.CharField(max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["carrier"].widget.attrs.setdefault("class", "form-control")


class WalletAmountForm(forms.Form):
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reference = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"].widget.attrs.setdefault("class", "form-control")
        self.fields["reference"].widget.attrs.setdefault("class", "form-control")


class SubscriptionPlanForm(forms.ModelForm):
    features_csv = forms.CharField(
        required=False,
        label="Features (comma separated)",
        help_text="Example: plugins,wallet,reviews",
    )

    class Meta:
        model = SubscriptionPlan
        fields = [
            "name",
            "price",
            "billing_cycle",
            "max_products",
            "max_orders_monthly",
            "max_staff_users",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.setdefault("class", "form-control")
        self.fields["price"].widget.attrs.setdefault("class", "form-control")
        self.fields["billing_cycle"].widget.attrs.setdefault("class", "form-select")
        self.fields["is_active"].widget.attrs.setdefault("class", "form-check-input")
        self.fields["features_csv"].widget.attrs.setdefault("class", "form-control")
        for field_name in ["max_products", "max_orders_monthly", "max_staff_users"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.setdefault("class", "form-control")

        if self.instance and self.instance.pk:
            self.fields["features_csv"].initial = ",".join(self.instance.features or [])

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        raw = self.cleaned_data.get("features_csv", "")
        instance.features = [s.strip() for s in raw.split(",") if s.strip()]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@login_required
@require_GET
@tenant_access_required
def dashboard(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    tenant = request.tenant
    store_profile = getattr(tenant, "store_profile", None)
    today = date.today()

    revenue_today = (
        Payment.objects.filter(
            order__store_id=store_id, status="success", created_at__date=today
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    orders_today = Order.objects.filter(store_id=store_id, created_at__date=today).count()
    active_shipments = Shipment.objects.filter(order__store_id=store_id).exclude(
        status__in=["delivered", "cancelled"]
    ).count()

    wallet = WalletService.get_or_create_wallet(store_id)
    categories = Category.objects.filter(store_id=store_id).order_by("name")[:12]
    latest_products = (
        Product.objects.filter(store_id=store_id)
        .select_related("inventory")
        .order_by("-id")[:8]
    )

    context = {
        "store_id": store_id,
        "tenant": tenant,
        "store_profile": store_profile,
        "revenue_today": revenue_today,
        "orders_today": orders_today,
        "wallet": wallet,
        "active_shipments": active_shipments,
        "products_count": Product.objects.filter(store_id=store_id).count(),
        "pending_reviews": Review.objects.filter(
            product__store_id=store_id, status="pending"
        ).count(),
        "categories": categories,
        "latest_products": latest_products,
    }
    return render(request, "web/dashboard.html", context)


@login_required
@require_GET
@tenant_access_required
def product_list(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    products = (
        Product.objects.filter(store_id=store_id)
        .prefetch_related("categories")
        .select_related("inventory")
        .order_by("-id")
    )
    return render(request, "web/products/list.html", {"products": products, "store_id": store_id})


@login_required
@require_http_methods(["GET", "POST"])
@tenant_access_required
def product_create(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    form = ProductForm(request.POST or None, request.FILES or None, store_id=store_id)
    if request.method == "POST" and form.is_valid():
        try:
            ProductService.create_product(
                store_id=store_id,
                sku=form.cleaned_data["sku"],
                name=form.cleaned_data["name"],
                price=form.cleaned_data["price"],
                image_file=form.cleaned_data.get("image"),
                categories=form.cleaned_data.get("categories"),
                quantity=form.cleaned_data["quantity"],
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Product created successfully.")
            return redirect("web:product_list")
    return render(request, "web/products/form.html", {"form": form, "mode": "create", "store_id": store_id})


@login_required
@require_http_methods(["GET", "POST"])
@tenant_access_required
def product_edit(request: HttpRequest, product_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    product = get_object_or_404(Product, pk=product_id, store_id=store_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product, store_id=store_id)
    if request.method == "POST" and form.is_valid():
        try:
            ProductService.update_product(
                store_id=store_id,
                product=product,
                sku=form.cleaned_data["sku"],
                name=form.cleaned_data["name"],
                price=form.cleaned_data["price"],
                image_file=form.cleaned_data.get("image"),
                categories=form.cleaned_data.get("categories"),
                quantity=form.cleaned_data["quantity"],
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Product updated successfully.")
            return redirect("web:product_list")
    return render(
        request,
        "web/products/form.html",
        {"form": form, "mode": "edit", "product": product},
    )


@login_required
@require_GET
@tenant_access_required
def order_list(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    orders = (
        Order.objects.filter(store_id=store_id).select_related("customer").order_by("-created_at")
    )
    return render(request, "web/orders/list.html", {"orders": orders, "store_id": store_id})


@login_required
@require_http_methods(["GET", "POST"])
@tenant_access_required
def order_create(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    order_form = OrderCreateForm(request.POST or None, store_id=store_id)
    formset = OrderItemFormSet(
        request.POST or None, prefix="items", form_kwargs={"store_id": store_id}
    )

    if request.method == "POST" and order_form.is_valid() and formset.is_valid():
        items = []
        for form in formset:
            if form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data:
                continue
            items.append(form.cleaned_data)

        if not items:
            messages.error(request, "Please add at least one item.")
        else:
            try:
                order = OrderService.create_order(
                    order_form.cleaned_data["customer"],
                    items,
                    store_id=store_id,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Order created successfully.")
                return redirect("web:order_detail", order_id=order.id)

    context = {"order_form": order_form, "formset": formset, "store_id": store_id}
    return render(request, "web/orders/create.html", context)


@login_required
@require_GET
@tenant_access_required
def order_detail(request: HttpRequest, order_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    order = get_object_or_404(
        Order.objects.select_related("customer"), pk=order_id, store_id=store_id
    )
    items = order.items.select_related("product").all()
    payments = Payment.objects.filter(order=order).order_by("-created_at")
    shipments = Shipment.objects.filter(order=order).order_by("-created_at")
    can_transition_to = OrderLifecycleService.allowed_transitions(order.status)
    ship_form = ShipmentCreateForm()

    context = {
        "store_id": store_id,
        "order": order,
        "items": items,
        "payments": payments,
        "shipments": shipments,
        "can_transition_to": can_transition_to,
        "ship_form": ship_form,
    }
    return render(request, "web/orders/detail.html", context)


@login_required
@require_POST
@tenant_access_required
def order_change_status(request: HttpRequest, order_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    order = get_object_or_404(Order, pk=order_id, store_id=store_id)
    new_status = (request.POST.get("status") or "").strip()
    try:
        OrderLifecycleService.transition(order=order, new_status=new_status)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Order status updated to {new_status}.")
    return redirect("web:order_detail", order_id=order.id)


@login_required
@require_POST
@tenant_access_required
def order_pay(request: HttpRequest, order_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    order = get_object_or_404(Order, pk=order_id, store_id=store_id)
    try:
        PaymentService.initiate_payment(order, method="card")
        messages.success(request, "Payment initiated successfully.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("web:order_detail", order_id=order.id)


@login_required
@require_POST
@tenant_access_required
def order_ship(request: HttpRequest, order_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    order = get_object_or_404(Order, pk=order_id, store_id=store_id)
    form = ShipmentCreateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please provide a carrier.")
        return redirect("web:order_detail", order_id=order.id)

    try:
        ShippingService.create_shipment(order, carrier=form.cleaned_data["carrier"])
        messages.success(request, "Shipment created successfully.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("web:order_detail", order_id=order.id)


@login_required
@require_GET
@tenant_access_required
def shipment_list(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    shipments = (
        Shipment.objects.filter(order__store_id=store_id)
        .select_related("order")
        .order_by("-created_at")
    )
    return render(request, "web/shipping/list.html", {"shipments": shipments, "store_id": store_id})


@login_required
@require_GET
@tenant_access_required
def wallet_detail(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    wallet = WalletService.get_or_create_wallet(store_id)
    transactions = wallet.transactions.order_by("-created_at")

    context = {
        "store_id": store_id,
        "wallet": wallet,
        "transactions": transactions,
        "credit_form": WalletAmountForm(),
        "debit_form": WalletAmountForm(),
    }
    return render(request, "web/wallet/detail.html", context)


@login_required
@require_POST
@tenant_access_required
def wallet_credit(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    wallet = WalletService.get_or_create_wallet(store_id)
    form = WalletAmountForm(request.POST)
    if form.is_valid():
        WalletService.credit(wallet, form.cleaned_data["amount"], form.cleaned_data["reference"])
        messages.success(request, "Wallet credited successfully.")
    else:
        messages.error(request, "Invalid credit request.")
    return redirect("web:wallet_detail")


@login_required
@require_POST
@tenant_access_required
def wallet_debit(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    wallet = WalletService.get_or_create_wallet(store_id)
    form = WalletAmountForm(request.POST)
    if form.is_valid():
        try:
            WalletService.debit(wallet, form.cleaned_data["amount"], form.cleaned_data["reference"])
            messages.success(request, "Wallet debited successfully.")
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Invalid debit request.")
    return redirect("web:wallet_detail")


@login_required
@require_GET
@tenant_access_required
def review_list(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    reviews = (
        Review.objects.filter(product__store_id=store_id)
        .select_related("product", "customer")
        .order_by("-created_at")
    )
    return render(request, "web/reviews/list.html", {"reviews": reviews, "store_id": store_id})


@login_required
@require_POST
@tenant_access_required
def review_approve(request: HttpRequest, review_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    review = get_object_or_404(Review, pk=review_id, product__store_id=store_id)
    ReviewService.approve_review(review)
    messages.success(request, "Review approved.")
    return redirect("web:review_list")


@login_required
@require_POST
@tenant_access_required
def review_reject(request: HttpRequest, review_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    review = get_object_or_404(Review, pk=review_id, product__store_id=store_id)
    ReviewService.reject_review(review)
    messages.success(request, "Review rejected.")
    return redirect("web:review_list")


@login_required
@require_GET
@tenant_access_required
def subscription_plans(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by("price", "name")
    active_sub = SubscriptionService.get_active_subscription(store_id)

    context = {
        "store_id": store_id,
        "plans": plans,
        "active_subscription": active_sub,
    }
    return render(request, "web/subscriptions/plans.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@tenant_access_required
def subscription_plan_create(request: HttpRequest) -> HttpResponse:
    form = SubscriptionPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan created successfully.")
        return redirect("web:subscription_plans")
    return render(request, "web/subscriptions/plan_form.html", {"form": form})


@login_required
@require_POST
@tenant_access_required
def subscribe_store(request: HttpRequest, plan_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
    SubscriptionService.subscribe_store(store_id, plan)
    messages.success(request, "Subscribed successfully.")
    return redirect("web:subscription_plans")


@login_required
@require_GET
@tenant_access_required
def plugin_store(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    plugins = Plugin.objects.filter(is_active=True).order_by("name")
    installed_ids = set(
        InstalledPlugin.objects.filter(store_id=store_id).values_list("plugin_id", flat=True)
    )
    active_sub = SubscriptionService.get_active_subscription(store_id)

    context = {
        "store_id": store_id,
        "plugins": plugins,
        "installed_ids": installed_ids,
        "active_subscription": active_sub,
    }
    return render(request, "web/plugins/store.html", context)


@login_required
@require_POST
@tenant_access_required
def plugin_install(request: HttpRequest, plugin_id: int) -> HttpResponse:
    store_id = _get_store_id(request)
    plugin = get_object_or_404(Plugin, pk=plugin_id, is_active=True)
    try:
        PluginInstallationService.install_plugin(store_id, plugin)
        messages.success(request, f"Plugin '{plugin.name}' installed.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("web:plugin_store")


@login_required
@require_GET
@tenant_access_required
def settings_view(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    tenant = request.tenant
    store_profile = getattr(tenant, "store_profile", None)
    active_sub = SubscriptionService.get_active_subscription(store_id)
    custom_domains = StoreDomain.objects.filter(tenant=tenant).order_by("-created_at")
    custom_domain_form = CustomDomainForm()

    server_ip = (getattr(settings, "CUSTOM_DOMAIN_SERVER_IP", "") or "").strip()
    cname_target = (getattr(settings, "CUSTOM_DOMAIN_CNAME_TARGET", "") or "").strip()
    if not cname_target:
        base_domain = normalize_domain(getattr(settings, "WASSLA_BASE_DOMAIN", ""))
        if base_domain:
            cname_target = f"stores.{base_domain}"
    verification_path_prefix = getattr(
        settings,
        "CUSTOM_DOMAIN_VERIFICATION_PATH_PREFIX",
        "/.well-known/wassla-domain-verification",
    )
    store_settings_form = StoreSettingsForm(
        initial={
            "name": tenant.name,
            "slug": tenant.slug,
            "currency": tenant.currency,
            "language": tenant.language,
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
        }
    )
    return render(
        request,
        "web/settings/index.html",
        {
            "store_id": store_id,
            "tenant": tenant,
            "store_profile": store_profile,
            "active_subscription": active_sub,
            "store_settings_form": store_settings_form,
            "custom_domains": custom_domains,
            "custom_domain_form": custom_domain_form,
            "custom_domain_server_ip": server_ip,
            "custom_domain_cname_target": cname_target,
            "custom_domain_verification_prefix": verification_path_prefix,
        },
    )


@require_GET
def landing(request: HttpRequest) -> HttpResponse:
    return render(request, "web/landing.html")


@login_required
@require_GET
@tenant_access_required
def category_list(request: HttpRequest) -> HttpResponse:
    store_id = _get_store_id(request)
    categories = Category.objects.filter(store_id=store_id).order_by("name")
    return render(request, "web/categories/list.html", {"store_id": store_id, "categories": categories})


@login_required
@require_GET
def account_home(request: HttpRequest) -> HttpResponse:
    return render(request, "web/account/index.html")


@login_required
@require_GET
def cart_home(request: HttpRequest) -> HttpResponse:
    return render(request, "web/cart/index.html")
