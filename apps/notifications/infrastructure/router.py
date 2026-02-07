from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.notifications.domain.errors import EmailGatewayError
from apps.notifications.domain.ports import EmailGateway
from apps.notifications.infrastructure.gateways.console import ConsoleEmailGateway
from apps.notifications.infrastructure.gateways.smtp import SmtpEmailGateway


@dataclass(frozen=True)
class ResolvedEmailProvider:
    gateway: EmailGateway
    provider_name: str
    default_from_email: str


class EmailGatewayRouter:
    @staticmethod
    def resolve() -> ResolvedEmailProvider:
        provider_name = getattr(settings, "EMAIL_PROVIDER", "console")
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

        if provider_name == "console":
            return ResolvedEmailProvider(gateway=ConsoleEmailGateway(), provider_name="console", default_from_email=default_from)

        if provider_name == "smtp":
            host = getattr(settings, "EMAIL_HOST", "")
            port = getattr(settings, "EMAIL_PORT", 587)
            user = getattr(settings, "EMAIL_HOST_USER", "")
            password = getattr(settings, "EMAIL_HOST_PASSWORD", "")
            use_tls = getattr(settings, "EMAIL_USE_TLS", True)
            if not host:
                raise EmailGatewayError("EMAIL_HOST is not configured.")
            return ResolvedEmailProvider(
                gateway=SmtpEmailGateway(host=host, port=port, username=user, password=password, use_tls=use_tls),
                provider_name="smtp",
                default_from_email=default_from,
            )

        raise EmailGatewayError(f"Unknown email provider: {provider_name}")

