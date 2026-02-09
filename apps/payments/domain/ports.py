from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentRedirect:
    redirect_url: str | None
    client_secret: str | None
    provider_reference: str | None


@dataclass(frozen=True)
class VerifiedEvent:
    event_id: str
    event_type: str
    intent_reference: str
    status: str


class PaymentGatewayPort(Protocol):
    code: str
    name: str

    def create_intent(self, *, order, amount, currency, return_url: str) -> PaymentRedirect:
        ...

    def verify_event(self, *, payload: dict, headers: dict) -> VerifiedEvent:
        ...

    def capture_or_confirm(self, *, intent_reference: str, event: VerifiedEvent | None = None) -> str:
        ...
