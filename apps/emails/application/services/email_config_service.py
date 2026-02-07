from __future__ import annotations

from dataclasses import dataclass

from apps.emails.application.services.crypto import CredentialCrypto
from apps.emails.models import GlobalEmailSettings


class EmailConfigMissing(Exception):
    pass


class EmailConfigDisabled(Exception):
    pass


class EmailConfigInvalid(Exception):
    pass


@dataclass(frozen=True)
class EmailConfig:
    provider: str
    host: str
    port: int
    username: str
    password: str
    from_email: str
    use_tls: bool
    enabled: bool


class EmailConfigService:
    @staticmethod
    def get_active_config() -> EmailConfig:
        qs = GlobalEmailSettings.objects.all().order_by("-updated_at")
        if not qs.exists():
            raise EmailConfigMissing("Global email settings are not configured.")
        if qs.count() > 1:
            raise EmailConfigInvalid("Multiple GlobalEmailSettings rows found.")
        settings_obj = qs.first()
        if not settings_obj:
            raise EmailConfigMissing("Global email settings are missing.")
        if not settings_obj.enabled:
            raise EmailConfigDisabled("Global email settings are disabled.")
        password = ""
        if settings_obj.password_encrypted:
            payload = CredentialCrypto.decrypt_json(settings_obj.password_encrypted)
            password = (payload.get("password") or "").strip()
        config = EmailConfig(
            provider=settings_obj.provider,
            host=(settings_obj.host or "").strip(),
            port=int(settings_obj.port),
            username=(settings_obj.username or "").strip(),
            password=password,
            from_email=(settings_obj.from_email or "").strip(),
            use_tls=bool(settings_obj.use_tls),
            enabled=bool(settings_obj.enabled),
        )
        EmailConfigService.validate_config(config)
        return config

    @staticmethod
    def validate_config(config: EmailConfig) -> None:
        if not config.enabled:
            raise EmailConfigDisabled("Global email settings are disabled.")
        if not config.from_email:
            raise EmailConfigInvalid("From email is required.")
        if config.provider == GlobalEmailSettings.PROVIDER_SMTP:
            if not config.host or not config.port or not config.username or not config.password:
                raise EmailConfigInvalid("SMTP configuration is incomplete.")
        elif config.provider == GlobalEmailSettings.PROVIDER_SENDGRID:
            if not config.password:
                raise EmailConfigInvalid("SendGrid API key is missing.")
        elif config.provider == GlobalEmailSettings.PROVIDER_MAILGUN:
            if not config.username or not config.password:
                raise EmailConfigInvalid("Mailgun domain or API key is missing.")
        elif config.provider == GlobalEmailSettings.PROVIDER_SES:
            raise EmailConfigInvalid("SES provider is not enabled in phase 1.")
        else:
            raise EmailConfigInvalid("Unknown email provider.")
