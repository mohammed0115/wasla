"""
URL configuration for wasla_sore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import error_views, i18n_views
from apps.observability.views.health import healthz, readyz
from apps.observability.views.metrics import metrics

handler403 = "wasla_sore.error_views.handle_403"
handler404 = "wasla_sore.error_views.handle_404"
handler500 = "wasla_sore.error_views.handle_500"

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("metrics", metrics, name="metrics"),
    path("", include("apps.system.interfaces.web.urls")),
    path("admin/settlements/", include("apps.settlements.interfaces.web.admin_urls")),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("lang/<str:code>/", i18n_views.switch_language, name="lang-switch"),
    path("api/", include("wasla_sore.api_urls")),
    path("auth/", include(("apps.accounts.interfaces.web.auth_urls", "auth"), namespace="auth")),
    path("accounts/", include("apps.accounts.interfaces.web.urls")),
    path(
        "onboarding/",
        include(("apps.accounts.interfaces.web.onboarding_urls", "onboarding"), namespace="onboarding"),
    ),
    path("", include("wasla_sore.web_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
