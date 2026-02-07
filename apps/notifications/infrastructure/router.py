from __future__ import annotations

from dataclasses import dataclass

from apps.notifications.domain.errors import EmailGatewayError
from apps.notifications.domain.ports import EmailGateway
from apps.notifications.infrastructure.gateways.smtp import SmtpEmailGateway
from apps.emails.application.services.email_config_service import (
    EmailConfigDisabled,
    EmailConfigInvalid,
    EmailConfigMissing,
    EmailConfigService,
)


@dataclass(frozen=True)
class ResolvedEmailProvider:
    gateway: EmailGateway
    provider_name: str
    default_from_email: str


class EmailGatewayRouter:
    @staticmethod
    def resolve() -> ResolvedEmailProvider:
        try:
            config = EmailConfigService.get_active_config()
        except (EmailConfigMissing, EmailConfigDisabled, EmailConfigInvalid) as exc:
            raise EmailGatewayError(str(exc)) from exc

        provider_name = config.provider
        default_from = config.from_email

        if provider_name == "smtp":
            return ResolvedEmailProvider(
                gateway=SmtpEmailGateway(
                    host=config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    use_tls=config.use_tls,
                ),
                provider_name="smtp",
                default_from_email=default_from,
            )

        if provider_name in ("sendgrid", "mailgun", "ses"):
            raise EmailGatewayError(f"Provider '{provider_name}' is not supported by notifications module.")

        raise EmailGatewayError(f"Unknown email provider: {provider_name}")
