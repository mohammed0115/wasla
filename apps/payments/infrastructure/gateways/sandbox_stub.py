from __future__ import annotations

from uuid import uuid4

from apps.payments.domain.ports import PaymentRedirect, VerifiedEvent


class SandboxStubGateway:
    code = "sandbox"
    name = "Sandbox Stub"
    _signature = "sandbox-secret"

    def create_intent(self, *, order, amount, currency, return_url: str) -> PaymentRedirect:
        reference = f"SANDBOX-{uuid4().hex[:12]}"
        redirect_url = f"{return_url}?provider=sandbox&intent={reference}"
        return PaymentRedirect(redirect_url=redirect_url, client_secret=None, provider_reference=reference)

    def verify_event(self, *, payload: dict, headers: dict) -> VerifiedEvent:
        signature = headers.get("X-Signature")
        if signature != self._signature:
            raise ValueError("Invalid signature.")
        event_id = payload.get("event_id") or ""
        intent_reference = payload.get("intent_reference") or ""
        status = payload.get("status") or "failed"
        if not event_id or not intent_reference:
            raise ValueError("Invalid payload.")
        return VerifiedEvent(event_id=event_id, event_type="payment", intent_reference=intent_reference, status=status)

    def capture_or_confirm(self, *, intent_reference: str, event: VerifiedEvent | None = None) -> str:
        return "requires_action"
