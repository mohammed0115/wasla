from __future__ import annotations

from apps.payments.domain.ports import PaymentGatewayPort
from apps.payments.infrastructure.gateways.dummy_gateway import DummyGateway
from apps.payments.infrastructure.gateways.sandbox_stub import SandboxStubGateway


class PaymentGatewayFacade:
    _registry: dict[str, PaymentGatewayPort] = {
        DummyGateway.code: DummyGateway(),
        SandboxStubGateway.code: SandboxStubGateway(),
    }

    @classmethod
    def get(cls, provider_code: str) -> PaymentGatewayPort:
        key = (provider_code or "").strip().lower()
        if key not in cls._registry:
            raise ValueError(f"Unknown payment provider: {provider_code}")
        return cls._registry[key]

    @classmethod
    def available_providers(cls) -> list[dict]:
        return [{"code": adapter.code, "name": adapter.name} for adapter in cls._registry.values()]
