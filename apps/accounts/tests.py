from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountProfile, OTPLog
from apps.emails.application.services.crypto import CredentialCrypto
from apps.emails.models import GlobalEmailSettings


class AccountsAuthApiTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        GlobalEmailSettings.objects.create(
            provider=GlobalEmailSettings.PROVIDER_SMTP,
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password_encrypted=CredentialCrypto.encrypt_text("secret"),
            from_email="no-reply@example.com",
            use_tls=True,
            enabled=True,
        )

    def test_register_api_contract_and_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            data={
                "full_name": "Merchant One",
                "phone": "0500000001",
                "email": "merchant1@example.com",
                "password": "StrongPass12345!",
                "accept_terms": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("data", payload)
        self.assertIn("next_step", payload)
        self.assertIn("access", payload["data"])
        self.assertIn("refresh", payload["data"])
        self.assertEqual(payload["next_step"], reverse("auth:otp_verify"))

        user = get_user_model().objects.get(pk=payload["data"]["user_id"])
        self.assertEqual(user.email, "merchant1@example.com")
        self.assertTrue(AccountProfile.objects.filter(user=user, phone="0500000001").exists())

    def test_login_api_works_with_phone_and_email(self):
        User = get_user_model()
        user = User.objects.create_user(username="0500000002", email="merchant2@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(
            user=user,
            full_name="Merchant Two",
            phone="0500000002",
            accepted_terms_at=timezone.now(),
        )

        phone_login = self.client.post(
            "/api/auth/login/",
            data={"identifier": "0500000002", "password": "StrongPass12345!"},
            format="json",
        )
        self.assertEqual(phone_login.status_code, 200)
        phone_payload = phone_login.json()
        self.assertTrue(phone_payload["success"])
        self.assertIn("access", phone_payload["data"])
        self.assertEqual(phone_payload["next_step"], reverse("auth:otp_verify"))

        email_login = self.client.post(
            "/api/auth/login/",
            data={"identifier": "merchant2@example.com", "password": "StrongPass12345!"},
            format="json",
        )
        self.assertEqual(email_login.status_code, 200)
        email_payload = email_login.json()
        self.assertTrue(email_payload["success"])
        self.assertIn("access", email_payload["data"])
        self.assertEqual(email_payload["next_step"], reverse("auth:otp_verify"))

    def test_email_otp_request_and_verify(self):
        import re

        from django.core import mail

        User = get_user_model()
        user = User.objects.create_user(username="0500000010", email="merchant10@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(
            user=user,
            full_name="Merchant Ten",
            phone="0500000010",
            accepted_terms_at=timezone.now(),
        )

        self.client.force_authenticate(user=user)

        with self.captureOnCommitCallbacks(execute=True):
            req = self.client.post("/api/auth/otp/request/", data={"purpose": "email_verify"}, format="json")
        self.assertEqual(req.status_code, 201)
        self.assertTrue(req.json()["success"])
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[-1]
        body = (email.body or "") + "\n" + "".join(a[0] for a in getattr(email, "alternatives", []) or [])
        code_match = re.search(r"\b\d{6}\b", body)
        self.assertIsNotNone(code_match)
        code = code_match.group(0)

        verify = self.client.post("/api/auth/otp/verify/", data={"purpose": "email_verify", "code": code}, format="json")
        self.assertEqual(verify.status_code, 200)
        payload = verify.json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["data"]["verified"])
        self.assertEqual(payload["next_step"], reverse("onboarding:country"))

        profile = AccountProfile.objects.get(user=user)
        self.assertIsNotNone(profile.email_verified_at)
        self.assertLess(profile.email_verified_at, timezone.now() + timezone.timedelta(seconds=5))

    def test_otp_login_request_and_verify(self):
        import re

        from django.core import mail

        User = get_user_model()
        user = User.objects.create_user(username="0500000020", email="merchant20@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(
            user=user,
            full_name="Merchant Twenty",
            phone="0500000020",
            accepted_terms_at=timezone.now(),
        )

        with self.captureOnCommitCallbacks(execute=True):
            req = self.client.post("/api/auth/otp/login/request/", data={"identifier": "merchant20@example.com"}, format="json")
        self.assertEqual(req.status_code, 201)
        self.assertTrue(req.json()["success"])
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[-1]
        body = (email.body or "") + "\n" + "".join(a[0] for a in getattr(email, "alternatives", []) or [])
        code_match = re.search(r"\b\d{6}\b", body)
        self.assertIsNotNone(code_match)
        code = code_match.group(0)

        verify = self.client.post(
            "/api/auth/otp/login/verify/",
            data={"identifier": "merchant20@example.com", "code": code},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        payload = verify.json()
        self.assertTrue(payload["success"])
        self.assertIn("access", payload["data"])

    def test_hybrid_otp_request_and_verify_creates_user(self):
        import re

        from django.core import mail

        with self.captureOnCommitCallbacks(execute=True):
            req = self.client.post("/api/auth/otp/request/", data={"identifier": "newuser@example.com"}, format="json")
        self.assertEqual(req.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[-1]
        body = (email.body or "") + "\n" + "".join(a[0] for a in getattr(email, "alternatives", []) or [])
        code = re.search(r"\b\d{6}\b", body).group(0)

        verify = self.client.post(
            "/api/auth/otp/verify/",
            data={"identifier": "newuser@example.com", "code": code},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        payload = verify.json()
        self.assertTrue(payload["success"])
        self.assertIn("access", payload["data"])

    def test_auth_start_api_for_existing_user(self):
        User = get_user_model()
        user = User.objects.create_user(username="0500000040", email="merchant40@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(
            user=user,
            full_name="Merchant Forty",
            phone="0500000040",
            accepted_terms_at=timezone.now(),
        )

        response = self.client.post("/api/auth/start/", data={"identifier": "merchant40@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["data"]["account_exists"])
        self.assertEqual(payload["data"]["default_method"], "otp")
        self.assertEqual(payload["next_step"], reverse("api_auth_otp_request"))

    def test_auth_start_api_for_new_user(self):
        response = self.client.post("/api/auth/start/", data={"identifier": "newuser@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertFalse(payload["data"]["account_exists"])
        self.assertTrue(payload["data"]["can_register"])
        self.assertEqual(payload["data"]["prefill"]["email"], "newuser@example.com")
        self.assertEqual(payload["next_step"], reverse("api_auth_otp_request"))

    def test_onboarding_apis_save_state(self):
        User = get_user_model()
        user = User.objects.create_user(username="0500000009", email="merchant9@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(
            user=user,
            full_name="Merchant Nine",
            phone="0500000009",
            accepted_terms_at=timezone.now(),
        )

        self.client.force_authenticate(user=user)

        country = self.client.post("/api/onboarding/country/", data={"country": "SA"}, format="json")
        self.assertEqual(country.status_code, 200)
        country_payload = country.json()
        self.assertTrue(country_payload["success"])
        self.assertEqual(country_payload["data"]["country"], "SA")
        self.assertEqual(country_payload["next_step"], reverse("onboarding:business_types"))

        business = self.client.post(
            "/api/onboarding/business-types/",
            data={"business_types": ["fashion", "electronics"]},
            format="json",
        )
        self.assertEqual(business.status_code, 200)
        business_payload = business.json()
        self.assertTrue(business_payload["success"])
        self.assertEqual(business_payload["data"]["business_types"], ["fashion", "electronics"])
        self.assertEqual(business_payload["next_step"], reverse("onboarding:store"))

        profile = AccountProfile.objects.get(user=user)
        self.assertEqual(profile.country, "SA")
        self.assertEqual(profile.business_types, ["fashion", "electronics"])


class AccountsAuthWebTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def test_signup_web_logs_in_and_redirects_to_onboarding(self):
        response = self.client.post(
            reverse("signup"),
            data={
                "full_name": "Merchant Web",
                "phone": "0500000003",
                "email": "merchant3@example.com",
                "password": "StrongPass12345!",
                "accept_terms": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertContains(response, "تأكيد البريد الإلكتروني")



class AccountsTestOtpPolicyTests(TestCase):
    @override_settings(DEBUG=True, ENVIRONMENT="development", TEST_OTP_CODE="12345")
    def test_test_otp_accepted_in_non_prod(self):
        from apps.accounts.application.use_cases.verify_otp import VerifyOtpCommand, VerifyOtpUseCase

        result = VerifyOtpUseCase.execute(
            VerifyOtpCommand(identifier="qa-user@example.com", code="12345", channel="email")
        )
        self.assertIsNotNone(result.user)
        self.assertTrue(OTPLog.objects.filter(identifier="qa-user@example.com", code_type=OTPLog.CODE_TYPE_TEST).exists())

    @override_settings(DEBUG=False, ENVIRONMENT="prod", TEST_OTP_CODE="12345")
    def test_test_otp_rejected_in_prod(self):
        from apps.accounts.application.use_cases.verify_otp import VerifyOtpCommand, VerifyOtpUseCase

        with self.assertRaises(ValueError):
            VerifyOtpUseCase.execute(
                VerifyOtpCommand(identifier="prod-user@example.com", code="12345", channel="email")
            )
        self.assertFalse(OTPLog.objects.filter(identifier="prod-user@example.com").exists())
