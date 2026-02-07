from django.urls import path

from .views import (
    auth_start_view,
    auth_verify_view,
    complete_profile_view,
    login_view,
    logout_view,
    otp_login_view,
    otp_verify_view,
    signup_view,
)

app_name = "auth"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", signup_view, name="register"),
    path("start/", auth_start_view, name="start"),
    path("verify/", auth_verify_view, name="verify"),
    path("complete-profile/", complete_profile_view, name="complete_profile"),
    path("otp-login/", otp_login_view, name="otp_login"),
    path("otp/", otp_verify_view, name="otp_verify"),
    path("logout/", logout_view, name="logout"),
]
