from __future__ import annotations

from django.test import TestCase, override_settings

from apps.notifications.application.use_cases.request_email_otp import RequestEmailOtpCommand, RequestEmailOtpUseCase
from apps.notifications.application.use_cases.send_email import SendEmailCommand, SendEmailUseCase
from apps.notifications.application.use_cases.verify_email_otp import VerifyEmailOtpCommand, VerifyEmailOtpUseCase
from apps.notifications.models import EmailOtp


class EmailModuleTests(TestCase):
    @override_settings(EMAIL_PROVIDER="console", DEFAULT_FROM_EMAIL="no-reply@example.com")
    def test_send_email_console(self):
        SendEmailUseCase.execute(
            SendEmailCommand(
                subject="Test",
                body="Hello",
                to_email="user@example.com",
            )
        )

    @override_settings(
        EMAIL_PROVIDER="console",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        EMAIL_OTP_TTL_MINUTES=5,
        EMAIL_OTP_SUBJECT="OTP",
        EMAIL_OTP_BODY="Your code is {code}",
    )
    def test_request_and_verify_otp(self):
        result = RequestEmailOtpUseCase.execute(
            RequestEmailOtpCommand(email="user@example.com", purpose=EmailOtp.PURPOSE_REGISTER)
        )
        self.assertIsNotNone(result.otp_id)

        otp = EmailOtp.objects.get(id=result.otp_id)
        self.assertIsNotNone(otp.expires_at)

        # Verify with wrong code
        bad = VerifyEmailOtpUseCase.execute(
            VerifyEmailOtpCommand(email="user@example.com", purpose=EmailOtp.PURPOSE_REGISTER, code="000000")
        )
        self.assertFalse(bad.success)

    @override_settings(EMAIL_PROVIDER="console", DEFAULT_FROM_EMAIL="no-reply@example.com")
    def test_verify_otp_success(self):
        otp, code = EmailOtp.create_otp(email="user2@example.com", purpose=EmailOtp.PURPOSE_LOGIN, ttl_minutes=5)
        ok = VerifyEmailOtpUseCase.execute(
            VerifyEmailOtpCommand(email="user2@example.com", purpose=EmailOtp.PURPOSE_LOGIN, code=code)
        )
        self.assertTrue(ok.success)
