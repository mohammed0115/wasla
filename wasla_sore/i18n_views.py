from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect
from django.utils import translation
from django.views.decorators.http import require_GET


@require_GET
def switch_language(request, code: str):
    supported = {lang_code for lang_code, _ in settings.LANGUAGES}
    language = code if code in supported else settings.LANGUAGE_CODE
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"
    if hasattr(request, "session"):
        request.session[translation.LANGUAGE_SESSION_KEY] = language
    translation.activate(language)
    response = redirect(next_url)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
    return response
