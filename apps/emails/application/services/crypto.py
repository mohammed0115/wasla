from __future__ import annotations

import base64
import json
import os
from typing import Any


class CredentialCrypto:
    """
    Vault-ready design:
    - In production, set EMAIL_CREDENTIALS_ENCRYPTION_KEY to a 32-byte urlsafe base64 key (Fernet key).
    - In dev/test, you may set EMAIL_CREDENTIALS_ALLOW_PLAINTEXT=1 to store plain JSON (not recommended).
    """

    @staticmethod
    def encrypt_json(data: dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        key = os.getenv("EMAIL_CREDENTIALS_ENCRYPTION_KEY", "").strip()
        if not key:
            if os.getenv("EMAIL_CREDENTIALS_ALLOW_PLAINTEXT", "").strip().lower() in ("1", "true", "yes"):
                return "plain:" + base64.b64encode(raw).decode("ascii")
            raise RuntimeError("EMAIL_CREDENTIALS_ENCRYPTION_KEY is not set (refusing to store credentials).")

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

        if token.startswith("plain:"):
            raw = base64.b64decode(token.removeprefix("plain:").encode("ascii"))
            return json.loads(raw.decode("utf-8"))

        if not token.startswith("fernet:"):
            raise RuntimeError("Unknown credentials encryption format.")

        key = os.getenv("EMAIL_CREDENTIALS_ENCRYPTION_KEY", "").strip()
        if not key:
            raise RuntimeError("EMAIL_CREDENTIALS_ENCRYPTION_KEY is not set (cannot decrypt credentials).")

        try:
            from cryptography.fernet import Fernet
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("cryptography is required for encrypted credentials.") from exc

        f = Fernet(key.encode("utf-8"))
        raw = f.decrypt(token.removeprefix("fernet:").encode("ascii"))
        return json.loads(raw.decode("utf-8"))

