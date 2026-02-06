from __future__ import annotations

import uuid

from django.core.mail import EmailMultiAlternatives

from apps.emails.domain.ports import EmailGatewayPort
from apps.emails.domain.types import EmailMessage, EmailSendResult


class SmtpEmailGateway(EmailGatewayPort):
    def __init__(self, *, from_email: str, from_name: str = ""):
        self._from_email = from_email
        self._from_name = from_name

    def send(self, *, message: EmailMessage) -> EmailSendResult:
        from_header = self._from_email
        if self._from_name:
            from_header = f"{self._from_name} <{self._from_email}>"

        email = EmailMultiAlternatives(
            subject=message.subject,
            body=message.text or "",
            from_email=from_header,
            to=[message.to_email],
            headers=dict(message.headers or {}),
        )
        if message.html:
            email.attach_alternative(message.html, "text/html")
        email.send(fail_silently=False)
        return EmailSendResult(provider_message_id=str(uuid.uuid4()))

