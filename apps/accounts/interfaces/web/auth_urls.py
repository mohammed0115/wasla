from django.urls import path

from .views import login_view, logout_view, otp_login_view, otp_verify_view, signup_view

app_name = "auth"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", signup_view, name="register"),
    path("otp-login/", otp_login_view, name="otp_login"),
    path("otp/", otp_verify_view, name="otp_verify"),
    path("logout/", logout_view, name="logout"),
]
