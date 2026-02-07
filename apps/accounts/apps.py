from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        from apps.accounts.domain.hybrid_policies import is_testing_otp_allowed

        env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
        if env in {"prod", "production"}:
            if getattr(settings, "DEBUG", False):
                raise ImproperlyConfigured("DEBUG must be False in production.")
            if is_testing_otp_allowed():
                raise ImproperlyConfigured("Test OTP is enabled in production. Disable DEBUG or set ENVIRONMENT correctly.")
