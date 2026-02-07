from __future__ import annotations

import smtplib
from email.message import EmailMessage

from apps.notifications.domain.errors import EmailGatewayError
from apps.notifications.domain.ports import EmailGateway


class SmtpEmailGateway(EmailGateway):
    name = "smtp"

    def __init__(self, *, host: str, port: int, username: str, password: str, use_tls: bool = True) -> None:
        self._host = host
        self._port = int(port)
        self._username = username
        self._password = password
        self._use_tls = bool(use_tls)

    def send_email(self, *, subject: str, body: str, to_email: str, from_email: str) -> None:
        try:
            msg = EmailMessage()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP(self._host, self._port) as server:
                if self._use_tls:
                    server.starttls()
                if self._username and self._password:
                    server.login(self._username, self._password)
                server.send_message(msg)
        except Exception as exc:  # pragma: no cover - network errors vary
            raise EmailGatewayError(str(exc)) from exc

