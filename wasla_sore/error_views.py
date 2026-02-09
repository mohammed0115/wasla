from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger("wasla.request")

def _resolve_error_base_template(request: HttpRequest) -> str:
    dashboard_prefixes = (
        "/dashboard",
        "/products",
        "/orders",
        "/wallet",
        "/reviews",
        "/subscriptions",
        "/app-store",
        "/shipments",
        "/settings",
        "/categories",
        "/account",
        "/store/setup",
        "/store/create",
    )
    if request.user.is_authenticated and request.path.startswith(dashboard_prefixes):
        return "layouts/dashboard_base.html"
    return "layouts/public_base.html"


def handle_403(request: HttpRequest, exception=None) -> HttpResponse:
    return render(
        request,
        "errors/403.html",
        {"base_template": _resolve_error_base_template(request)},
        status=403,
    )


def handle_404(request: HttpRequest, exception=None) -> HttpResponse:
    return render(
        request,
        "errors/404.html",
        {"base_template": _resolve_error_base_template(request)},
        status=404,
    )


def handle_500(request: HttpRequest) -> HttpResponse:
    logger.error(
        "server_error",
        extra={"status_code": 500, "error_code": "server_error"},
    )
    return render(
        request,
        "errors/500.html",
        {"base_template": _resolve_error_base_template(request)},
        status=500,
    )
