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
