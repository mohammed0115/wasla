from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.emails.application.services.crypto import CredentialCrypto
from apps.emails.domain.ports import EmailGatewayPort, TemplateRendererPort
from apps.emails.infrastructure.providers.mailgun_gateway import MailgunEmailGateway
from apps.emails.infrastructure.providers.sendgrid_gateway import SendGridEmailGateway
from apps.emails.infrastructure.providers.smtp_gateway import SmtpEmailGateway
from apps.emails.infrastructure.renderers.django_renderer import DjangoTemplateRendererAdapter
from apps.emails.models import TenantEmailSettings


class EmailSettingsDisabled(Exception):
    pass


class EmailProviderNotConfigured(Exception):
    pass


@dataclass(frozen=True)
class ResolvedEmailBackend:
    provider: str
    from_email: str
    from_name: str
    gateway: EmailGatewayPort
    renderer: TemplateRendererPort


class TenantEmailProviderResolver:
    @staticmethod
    def resolve(*, tenant_id: int) -> ResolvedEmailBackend:
        settings_obj = TenantEmailSettings.objects.filter(tenant_id=tenant_id).first()
        if settings_obj and not settings_obj.is_enabled:
            raise EmailSettingsDisabled("Email sending is disabled for this tenant.")

        provider = (settings_obj.provider if settings_obj else TenantEmailSettings.PROVIDER_SMTP) or TenantEmailSettings.PROVIDER_SMTP
        from_email = (settings_obj.from_email if settings_obj else "") or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
        from_name = (settings_obj.from_name if settings_obj else "") or ""

        creds: dict[str, Any] = {}
        if settings_obj and settings_obj.credentials_encrypted:
            creds = CredentialCrypto.decrypt_json(settings_obj.credentials_encrypted)

        renderer: TemplateRendererPort = DjangoTemplateRendererAdapter()

        if provider == TenantEmailSettings.PROVIDER_SMTP:
            smtp_host = (creds.get("host") or "").strip() or None
            smtp_port = creds.get("port")
            try:
                smtp_port = int(smtp_port) if smtp_port is not None and str(smtp_port).strip() else None
            except Exception:
                smtp_port = None
            smtp_username = (creds.get("username") or "").strip() or None
            smtp_password = (creds.get("password") or "").strip() or None
            smtp_use_tls = creds.get("use_tls")
            smtp_use_ssl = creds.get("use_ssl")
            smtp_timeout = creds.get("timeout")
            try:
                smtp_timeout = int(smtp_timeout) if smtp_timeout is not None and str(smtp_timeout).strip() else None
            except Exception:
                smtp_timeout = None
            gateway = SmtpEmailGateway(
                from_email=from_email,
                from_name=from_name,
                host=smtp_host,
                port=smtp_port,
                username=smtp_username,
                password=smtp_password,
                use_tls=bool(smtp_use_tls) if smtp_use_tls is not None else None,
                use_ssl=bool(smtp_use_ssl) if smtp_use_ssl is not None else None,
                timeout=smtp_timeout,
            )
        elif provider == TenantEmailSettings.PROVIDER_SENDGRID:
            api_key = (creds.get("api_key") or "").strip()
            if not api_key:
                raise EmailProviderNotConfigured("SendGrid api_key missing in tenant credentials.")
            gateway = SendGridEmailGateway(api_key=api_key, from_email=from_email, from_name=from_name)
        elif provider == TenantEmailSettings.PROVIDER_MAILGUN:
            api_key = (creds.get("api_key") or "").strip()
            domain = (creds.get("domain") or "").strip()
            base_url = (creds.get("base_url") or "https://api.mailgun.net").strip()
            if not api_key or not domain:
                raise EmailProviderNotConfigured("Mailgun api_key/domain missing in tenant credentials.")
            gateway = MailgunEmailGateway(api_key=api_key, domain=domain, base_url=base_url, from_email=from_email, from_name=from_name)
        elif provider == TenantEmailSettings.PROVIDER_SES:
            raise EmailProviderNotConfigured("SES provider is optional and not enabled in phase 1.")
        else:
            raise EmailProviderNotConfigured(f"Unknown email provider: {provider!r}")

        return ResolvedEmailBackend(
            provider=provider,
            from_email=from_email,
            from_name=from_name,
            gateway=gateway,
            renderer=renderer,
        )
