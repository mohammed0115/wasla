from django.urls import path

from .views import login_view, logout_view, signup_view

app_name = "auth"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", signup_view, name="register"),
    path("logout/", logout_view, name="logout"),
]

