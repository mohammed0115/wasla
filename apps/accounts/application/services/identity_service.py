from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.accounts.domain.errors import AccountNotFoundError, AccountValidationError
from apps.accounts.domain.policies import normalize_email, normalize_phone
from apps.accounts.models import AccountProfile


class AccountIdentityService:
    @staticmethod
    def resolve_user_by_identifier(*, identifier: str):
        raw = (identifier or "").strip()
        if not raw:
            raise AccountValidationError("Identifier is required.", field="identifier")

        UserModel = get_user_model()
        user = None
        if "@" in raw:
            email = normalize_email(raw)
            user = UserModel.objects.filter(email__iexact=email).first()
        else:
            phone = normalize_phone(raw)
            user = UserModel.objects.filter(username__iexact=phone).first()
            if not user:
                profile = AccountProfile.objects.select_related("user").filter(phone=phone).first()
                user = profile.user if profile else None

        if not user:
            raise AccountNotFoundError("Account not found.")
        return user
