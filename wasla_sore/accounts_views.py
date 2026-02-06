from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("web:dashboard")

    form = UserCreationForm(request.POST or None)
    for field_name in ["username", "password1", "password2"]:
        if field_name in form.fields:
            form.fields[field_name].widget.attrs.setdefault("class", "form-control")
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("web:dashboard_setup_store")

    return render(request, "registration/signup.html", {"form": form})
