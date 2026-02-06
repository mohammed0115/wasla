from django.urls import path

from .views import LoginAPI, RegisterMerchantAPI

urlpatterns = [
    path("auth/register/", RegisterMerchantAPI.as_view(), name="api_auth_register"),
    path("auth/login/", LoginAPI.as_view(), name="api_auth_login"),
]

