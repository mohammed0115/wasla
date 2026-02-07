from django.urls import path

from . import onboarding_views

app_name = "onboarding"

urlpatterns = [
    path("", onboarding_views.start, name="start"),
    path("country/", onboarding_views.country, name="country"),
    path("business-types/", onboarding_views.business_types, name="business_types"),
    path("store/", onboarding_views.store, name="store"),
]
