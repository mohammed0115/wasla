"""
API URL aggregation.

AR: يجمع مسارات API من الموديولات المختلفة تحت `/api/`.
EN: Aggregates app API routes under `/api/`.
"""

from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("", include("apps.accounts.interfaces.api.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.orders.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.payments.interfaces.api.urls")),
    path("", include("apps.cart.interfaces.api.urls")),
    path("", include("apps.checkout.interfaces.api.urls")),
    path("", include("apps.webhooks.interfaces.api.urls")),
    path("", include("apps.settlements.interfaces.api.urls")),
    path("", include("apps.imports.interfaces.api.urls")),
    path("", include("apps.themes.interfaces.api.urls")),
    path("", include("apps.exports.interfaces.api.urls")),
    path("", include("apps.ai.interfaces.api.urls")),
    path("", include("apps.domains.interfaces.api_urls")),
    path("", include("apps.analytics.interfaces.api.urls")),
    path("system/", include("apps.system.interfaces.api.urls")),
    path("", include("apps.shipping.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.subscriptions.urls")),
    path("", include("apps.wallet.urls")),
    path("", include("apps.plugins.urls")),
    path("", include("apps.emails.urls")),
]
