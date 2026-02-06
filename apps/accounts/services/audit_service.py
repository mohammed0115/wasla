from __future__ import annotations

from apps.accounts.models import AccountAuditLog


class AccountAuditService:
    ACTION_REGISTERED = AccountAuditLog.ACTION_REGISTERED
    ACTION_LOGIN_SUCCEEDED = AccountAuditLog.ACTION_LOGIN_SUCCEEDED
    ACTION_LOGIN_FAILED = AccountAuditLog.ACTION_LOGIN_FAILED

    @staticmethod
    def record_action(
        *,
        user: object | None,
        action: str,
        ip_address: str | None = None,
        user_agent: str = "",
        metadata: dict | None = None,
    ) -> AccountAuditLog:
        user_id = getattr(user, "id", None) if user is not None else None
        return AccountAuditLog.objects.create(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent or "",
            metadata=metadata or {},
        )

