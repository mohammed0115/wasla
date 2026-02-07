from __future__ import annotations

from django.conf import settings
from django.db import models


class AccountProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    full_name = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=32, unique=True)
    country = models.CharField(max_length=10, blank=True, default="")
    business_types = models.JSONField(default=list, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AccountProfile(user_id={self.user_id}, phone={self.phone})"


class AccountAuditLog(models.Model):
    ACTION_REGISTERED = "registered"
    ACTION_LOGIN_SUCCEEDED = "login_succeeded"
    ACTION_LOGIN_FAILED = "login_failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_audit_logs",
    )
    action = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AccountAuditLog(action={self.action}, user_id={self.user_id})"


class AccountEmailOtp(models.Model):
    PURPOSE_EMAIL_VERIFY = "email_verify"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_LOGIN = "login"

    PURPOSE_CHOICES = [
        (PURPOSE_EMAIL_VERIFY, "Email Verify"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
        (PURPOSE_LOGIN, "Login"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"AccountEmailOtp(user_id={self.user_id}, purpose={self.purpose}, consumed={bool(self.consumed_at)})"
