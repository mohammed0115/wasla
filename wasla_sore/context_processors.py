from __future__ import annotations

from django.utils import translation


def language_meta(request):
    return {
        "CURRENT_LANGUAGE_CODE": translation.get_language(),
        "LANGUAGE_DIR": "rtl" if translation.get_language_bidi() else "ltr",
    }
