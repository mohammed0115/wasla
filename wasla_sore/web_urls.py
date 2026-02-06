from django.urls import path

from . import web_views
from apps.tenants.interfaces.web import views as tenant_web_views
from apps.tenants.interfaces.web import storefront_views as tenant_storefront_views

app_name = "web"

urlpatterns = [
    path("dashboard/", web_views.dashboard, name="dashboard"),
    path("", web_views.landing, name="landing"),
    path("categories/", web_views.category_list, name="categories"),
    path("account/", web_views.account_home, name="account"),
    path("cart/", web_views.cart_home, name="cart"),
    path("dashboard/setup/store/", tenant_web_views.dashboard_setup_store, name="dashboard_setup_store"),
    path("dashboard/setup/payment/", tenant_web_views.dashboard_setup_payment, name="dashboard_setup_payment"),
    path("dashboard/setup/shipping/", tenant_web_views.dashboard_setup_shipping, name="dashboard_setup_shipping"),
    path("dashboard/setup/activate/", tenant_web_views.dashboard_setup_activate, name="dashboard_setup_activate"),
    path("store/", tenant_storefront_views.storefront_home, name="storefront_home"),
    path("store/create/", tenant_web_views.store_create, name="store_create"),
    path("store/setup/", tenant_web_views.store_setup_start, name="store_setup_start"),
    path("store/setup/1/", tenant_web_views.store_setup_step1, name="store_setup_step1"),
    path("store/setup/2/", tenant_web_views.store_setup_step2, name="store_setup_step2"),
    path("store/setup/3/", tenant_web_views.store_setup_step3, name="store_setup_step3"),
    path("store/setup/4/", tenant_web_views.store_setup_step4, name="store_setup_step4"),
    path("products/", web_views.product_list, name="product_list"),
    path("products/new/", web_views.product_create, name="product_create"),
    path("products/<int:product_id>/edit/", web_views.product_edit, name="product_edit"),
    path("orders/", web_views.order_list, name="order_list"),
    path("orders/new/", web_views.order_create, name="order_create"),
    path("orders/<int:order_id>/", web_views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/status/", web_views.order_change_status, name="order_change_status"),
    path("orders/<int:order_id>/pay/", web_views.order_pay, name="order_pay"),
    path("orders/<int:order_id>/ship/", web_views.order_ship, name="order_ship"),
    path("shipments/", web_views.shipment_list, name="shipment_list"),
    path("wallet/", web_views.wallet_detail, name="wallet_detail"),
    path("wallet/credit/", web_views.wallet_credit, name="wallet_credit"),
    path("wallet/debit/", web_views.wallet_debit, name="wallet_debit"),
    path("reviews/", web_views.review_list, name="review_list"),
    path("reviews/<int:review_id>/approve/", web_views.review_approve, name="review_approve"),
    path("reviews/<int:review_id>/reject/", web_views.review_reject, name="review_reject"),
    path("subscriptions/", web_views.subscription_plans, name="subscription_plans"),
    path("subscriptions/new/", web_views.subscription_plan_create, name="subscription_plan_create"),
    path("subscriptions/<int:plan_id>/subscribe/", web_views.subscribe_store, name="subscribe_store"),
    path("app-store/", web_views.plugin_store, name="plugin_store"),
    path("app-store/<int:plugin_id>/install/", web_views.plugin_install, name="plugin_install"),
    path("settings/", web_views.settings_view, name="settings"),
    path("settings/store/update/", tenant_web_views.store_settings_update, name="store_settings_update"),
]
