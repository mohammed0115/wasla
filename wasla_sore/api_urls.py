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
    path("", include("apps.shipping.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.subscriptions.urls")),
    path("", include("apps.wallet.urls")),
    path("", include("apps.plugins.urls")),
    path("", include("apps.emails.urls")),
]
