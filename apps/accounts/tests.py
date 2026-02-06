from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import AccountProfile


class AccountsAuthApiTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()

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
        self.assertEqual(payload["next_step"], reverse("onboarding:country"))

        user = get_user_model().objects.get(pk=payload["data"]["user_id"])
        self.assertEqual(user.email, "merchant1@example.com")
        self.assertTrue(AccountProfile.objects.filter(user=user, phone="0500000001").exists())

    def test_login_api_works_with_phone_and_email(self):
        User = get_user_model()
        user = User.objects.create_user(username="0500000002", email="merchant2@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(user=user, full_name="Merchant Two", phone="0500000002")

        phone_login = self.client.post(
            "/api/auth/login/",
            data={"identifier": "0500000002", "password": "StrongPass12345!"},
            format="json",
        )
        self.assertEqual(phone_login.status_code, 200)
        phone_payload = phone_login.json()
        self.assertTrue(phone_payload["success"])
        self.assertIn("access", phone_payload["data"])
        self.assertEqual(phone_payload["next_step"], reverse("onboarding:country"))

        email_login = self.client.post(
            "/api/auth/login/",
            data={"identifier": "merchant2@example.com", "password": "StrongPass12345!"},
            format="json",
        )
        self.assertEqual(email_login.status_code, 200)
        email_payload = email_login.json()
        self.assertTrue(email_payload["success"])
        self.assertIn("access", email_payload["data"])
        self.assertEqual(email_payload["next_step"], reverse("onboarding:country"))

    def test_onboarding_apis_save_state(self):
        User = get_user_model()
        user = User.objects.create_user(username="0500000009", email="merchant9@example.com", password="StrongPass12345!")
        AccountProfile.objects.create(user=user, full_name="Merchant Nine", phone="0500000009")

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
        self.assertEqual(business_payload["next_step"], reverse("web:dashboard_setup_store"))

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
        self.assertContains(response, "اختر دولتك")
