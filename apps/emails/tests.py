from __future__ import annotations

import os

from django.core import mail
from django.test import TestCase

from apps.emails.application.services.crypto import CredentialCrypto
from apps.emails.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase
from apps.emails.models import EmailLog, TenantEmailSettings
from apps.tenants.models import Tenant


class EmailGatewayTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tenant = Tenant.objects.create(slug="t1", name="T1", is_active=True, currency="SAR", language="ar")
        TenantEmailSettings.objects.create(
            tenant=self.tenant,
            provider=TenantEmailSettings.PROVIDER_SMTP,
            from_email="no-reply@example.com",
            from_name="Wasla",
            is_enabled=True,
        )

    def test_send_email_is_idempotent(self):
        self.assertEqual(len(mail.outbox), 0)
        cmd = SendEmailCommand(
            tenant_id=self.tenant.id,
            to_email="user@example.com",
            template_key="welcome",
            context={"full_name": "User"},
            idempotency_key="k1",
        )
        with self.captureOnCommitCallbacks(execute=True):
            log1 = SendEmailUseCase.execute(cmd)
        with self.captureOnCommitCallbacks(execute=True):
            log2 = SendEmailUseCase.execute(cmd)
        self.assertEqual(log1.id, log2.id)
        self.assertEqual(EmailLog.objects.filter(tenant=self.tenant, idempotency_key="k1").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_credentials_crypto_requires_key_unless_plaintext_allowed(self):
        old_key = os.environ.pop("EMAIL_CREDENTIALS_ENCRYPTION_KEY", None)
        old_plain = os.environ.pop("EMAIL_CREDENTIALS_ALLOW_PLAINTEXT", None)
        try:
            with self.assertRaises(RuntimeError):
                CredentialCrypto.encrypt_json({"api_key": "x"})
            os.environ["EMAIL_CREDENTIALS_ALLOW_PLAINTEXT"] = "1"
            token = CredentialCrypto.encrypt_json({"api_key": "x"})
            self.assertTrue(token.startswith("plain:"))
            self.assertEqual(CredentialCrypto.decrypt_json(token)["api_key"], "x")
        finally:
            if old_key is not None:
                os.environ["EMAIL_CREDENTIALS_ENCRYPTION_KEY"] = old_key
            if old_plain is not None:
                os.environ["EMAIL_CREDENTIALS_ALLOW_PLAINTEXT"] = old_plain
