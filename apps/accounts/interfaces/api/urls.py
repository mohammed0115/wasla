from django.urls import path

from .views import (
    LoginAPI,
    OtpLoginRequestAPI,
    OtpLoginVerifyAPI,
    OtpRequestAPI,
    OtpVerifyAPI,
    RegisterMerchantAPI,
    SelectBusinessTypesAPI,
    SelectCountryAPI,
)

urlpatterns = [
    path("auth/register/", RegisterMerchantAPI.as_view(), name="api_auth_register"),
    path("auth/login/", LoginAPI.as_view(), name="api_auth_login"),
    path("auth/otp/login/request/", OtpLoginRequestAPI.as_view(), name="api_auth_otp_login_request"),
    path("auth/otp/login/verify/", OtpLoginVerifyAPI.as_view(), name="api_auth_otp_login_verify"),
    path("auth/otp/request/", OtpRequestAPI.as_view(), name="api_auth_otp_request"),
    path("auth/otp/verify/", OtpVerifyAPI.as_view(), name="api_auth_otp_verify"),
    path("onboarding/country/", SelectCountryAPI.as_view(), name="api_onboarding_country"),
    path(
        "onboarding/business-types/",
        SelectBusinessTypesAPI.as_view(),
        name="api_onboarding_business_types",
    ),
]
