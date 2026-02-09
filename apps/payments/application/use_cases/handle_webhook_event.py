from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services.order_service import OrderService
from apps.orders.application.use_cases.notify_merchant_order_placed import (
    NotifyMerchantOrderPlacedCommand,
    NotifyMerchantOrderPlacedUseCase,
)
from apps.payments.application.facade import PaymentGatewayFacade
from apps.payments.models import Payment, PaymentIntent, PaymentEvent
from apps.settlements.application.use_cases.credit_order_payment import (
    CreditOrderPaymentCommand,
    CreditOrderPaymentUseCase,
)
from apps.webhooks.models import WebhookEvent
from apps.analytics.application.telemetry import TelemetryService, actor_from_tenant_ctx
from apps.analytics.domain.types import ObjectRef
from apps.tenants.domain.tenant_context import TenantContext


@dataclass(frozen=True)
class HandleWebhookEventCommand:
    provider_code: str
    headers: dict
    payload: dict


class HandleWebhookEventUseCase:
    @staticmethod
    @transaction.atomic
    def execute(cmd: HandleWebhookEventCommand) -> WebhookEvent:
        gateway = PaymentGatewayFacade.get(cmd.provider_code)
        verified = gateway.verify_event(payload=cmd.payload, headers=cmd.headers)
        idempotency_key = f"{cmd.provider_code}:{verified.event_id}"

        event = WebhookEvent.objects.select_for_update().filter(idempotency_key=idempotency_key).first()
        if event and event.processing_status == WebhookEvent.STATUS_PROCESSED:
            return event

        if not event:
            event = WebhookEvent.objects.create(
                provider_code=cmd.provider_code,
                event_id=verified.event_id,
                idempotency_key=idempotency_key,
                payload_json=cmd.payload,
                processing_status=WebhookEvent.STATUS_PENDING,
            )

        PaymentEvent.objects.create(
            provider_code=cmd.provider_code,
            event_id=verified.event_id,
            payload_json=cmd.payload,
        )

        intent = PaymentIntent.objects.select_for_update().filter(
            provider_code=cmd.provider_code,
            provider_reference=verified.intent_reference,
        ).first()
        if not intent:
            event.processing_status = WebhookEvent.STATUS_FAILED
            event.processed_at = timezone.now()
            event.save(update_fields=["processing_status", "processed_at"])
            return event

        if verified.status == "succeeded" and intent.status != "succeeded":
            intent.status = "succeeded"
            intent.save(update_fields=["status"])
            order = Order.objects.select_for_update().filter(id=intent.order_id, store_id=intent.store_id).first()
            if order:
                OrderService.mark_as_paid(order)
                order.payment_status = "paid"
                order.save(update_fields=["payment_status"])
                Payment.objects.create(
                    order=order,
                    method=intent.provider_code,
                    status="success",
                    amount=intent.amount,
                    reference=intent.provider_reference or intent.idempotency_key,
                )
                CreditOrderPaymentUseCase.execute(CreditOrderPaymentCommand(order_id=order.id))
                NotifyMerchantOrderPlacedUseCase.execute(
                    NotifyMerchantOrderPlacedCommand(order_id=order.id, tenant_id=order.store_id)
                )
                tenant_ctx = TenantContext(
                    tenant_id=order.store_id,
                    currency=order.currency,
                    user_id=None,
                    session_key="",
                )
                TelemetryService.track(
                    event_name="payment.succeeded",
                    tenant_ctx=tenant_ctx,
                    actor_ctx=actor_from_tenant_ctx(tenant_ctx=tenant_ctx, actor_type="CUSTOMER"),
                    object_ref=ObjectRef(object_type="ORDER", object_id=order.id),
                    properties={"provider_code": intent.provider_code, "amount": str(intent.amount)},
                )

        if verified.status == "failed":
            intent.status = "failed"
            intent.save(update_fields=["status"])
            order = Order.objects.select_for_update().filter(id=intent.order_id, store_id=intent.store_id).first()
            if order:
                order.payment_status = "failed"
                order.save(update_fields=["payment_status"])
                tenant_ctx = TenantContext(
                    tenant_id=order.store_id,
                    currency=order.currency,
                    user_id=None,
                    session_key="",
                )
                TelemetryService.track(
                    event_name="payment.failed",
                    tenant_ctx=tenant_ctx,
                    actor_ctx=actor_from_tenant_ctx(tenant_ctx=tenant_ctx, actor_type="CUSTOMER"),
                    object_ref=ObjectRef(object_type="ORDER", object_id=order.id),
                    properties={"provider_code": intent.provider_code, "reason_code": "provider_failed"},
                )

        event.processing_status = WebhookEvent.STATUS_PROCESSED
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_status", "processed_at"])
        return event
