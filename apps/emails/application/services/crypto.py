from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from django.conf import settings


class CredentialCrypto:
    """
    Vault-ready design:
    - In production, set EMAIL_CREDENTIALS_ENCRYPTION_KEY to a 32-byte urlsafe base64 key (Fernet key).
    - In dev/test, you may set EMAIL_CREDENTIALS_ALLOW_PLAINTEXT=1 to store plain JSON (not recommended).
    """

    @staticmethod
    def encrypt_json(data: dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        key = os.getenv("EMAIL_CREDENTIALS_ENCRYPTION_KEY", "").strip() or CredentialCrypto._derived_fernet_key()

        try:
            from cryptography.fernet import Fernet
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("cryptography is required for encrypted credentials.") from exc

        f = Fernet(key.encode("utf-8"))
        token = f.encrypt(raw)
        return "fernet:" + token.decode("ascii")

    @staticmethod
    def decrypt_json(token: str) -> dict[str, Any]:
        token = (token or "").strip()
        if not token:
            return {}

        if not token.startswith("fernet:"):
            raise RuntimeError("Unknown credentials encryption format.")

        key = os.getenv("EMAIL_CREDENTIALS_ENCRYPTION_KEY", "").strip() or CredentialCrypto._derived_fernet_key()

        try:
            from cryptography.fernet import Fernet
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("cryptography is required for encrypted credentials.") from exc

        f = Fernet(key.encode("utf-8"))
        raw = f.decrypt(token.removeprefix("fernet:").encode("ascii"))
        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def _derived_fernet_key() -> str:
        """
        Derive a stable Fernet key from Django SECRET_KEY.
        This keeps provider credentials out of env files while still encrypting at rest.
        """
        secret = (getattr(settings, "SECRET_KEY", "") or "").encode("utf-8")
        if not secret:
            raise RuntimeError("SECRET_KEY is missing; cannot derive credentials encryption key.")
        digest = hashlib.sha256(secret + b"|emails.credentials.v1").digest()
        return base64.urlsafe_b64encode(digest).decode("ascii")
