from __future__ import annotations

import importlib

from django.conf import settings

from apps.accounts.domain.ports import OTPProviderPort


class OTPProviderResolver:
    @staticmethod
    def resolve(channel: str) -> OTPProviderPort:
        registry = getattr(settings, "OTP_PROVIDER_REGISTRY", {})
        dotted = registry.get(channel)
        if not dotted:
            raise ValueError(f"No OTP provider configured for channel '{channel}'.")
        module_path, class_name = dotted.rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
        return provider_cls()
