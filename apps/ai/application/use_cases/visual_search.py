from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from django.core.files.storage import default_storage
from django.db import transaction

from apps.ai.application.use_cases.log_ai_request import LogAIRequestCommand, LogAIRequestUseCase
from apps.ai.domain.policies import validate_image_upload
from apps.ai.domain.types import SearchResult
from apps.ai.infrastructure.embeddings.image_embedder import ImageEmbedder
from apps.ai.infrastructure.embeddings.vector_store_stub import search_similar, upsert_embedding
from apps.ai.infrastructure.providers.registry import get_provider
from apps.ai.models import AIProductEmbedding
from apps.catalog.models import Product
from apps.tenants.domain.tenant_context import TenantContext
from apps.analytics.application.telemetry import TelemetryService, actor_from_tenant_ctx


@dataclass(frozen=True)
class VisualSearchCommand:
    tenant_ctx: TenantContext
    image_file: object
    top_n: int = 5


class VisualSearchUseCase:
    @staticmethod
    def execute(cmd: VisualSearchCommand) -> SearchResult:
        provider = get_provider()
        started = monotonic()
        warnings: list[str] = []
        try:
            validate_image_upload(cmd.image_file)
            query_vector = ImageEmbedder.embed_uploaded(cmd.image_file)
            _ensure_embeddings(cmd.tenant_ctx.tenant_id, provider_code=getattr(provider, "code", ""))
            results = search_similar(store_id=cmd.tenant_ctx.tenant_id, vector=query_vector, top_n=cmd.top_n)
            data = [
                {
                    "product_id": item["product"].id,
                    "name": item["product"].name,
                    "score": round(item["score"], 4),
                }
                for item in results
            ]
            LogAIRequestUseCase.execute(
                LogAIRequestCommand(
                    store_id=cmd.tenant_ctx.tenant_id,
                    feature="SEARCH",
                    provider=getattr(provider, "code", ""),
                    latency_ms=int((monotonic() - started) * 1000),
                    token_count=None,
                    cost_estimate=0,
                    status="SUCCESS",
                )
            )
            TelemetryService.track(
                event_name="ai.visual_search_used",
                tenant_ctx=cmd.tenant_ctx,
                actor_ctx=actor_from_tenant_ctx(tenant_ctx=cmd.tenant_ctx, actor_type="MERCHANT"),
                properties={
                    "status": "success",
                    "result_count": len(data),
                    "provider_code": getattr(provider, "code", ""),
                },
            )
            return SearchResult(results=data, provider=getattr(provider, "code", ""), warnings=warnings)
        except Exception:
            LogAIRequestUseCase.execute(
                LogAIRequestCommand(
                    store_id=cmd.tenant_ctx.tenant_id,
                    feature="SEARCH",
                    provider=getattr(provider, "code", ""),
                    latency_ms=int((monotonic() - started) * 1000),
                    token_count=None,
                    cost_estimate=0,
                    status="FAILED",
                )
            )
            TelemetryService.track(
                event_name="ai.visual_search_used",
                tenant_ctx=cmd.tenant_ctx,
                actor_ctx=actor_from_tenant_ctx(tenant_ctx=cmd.tenant_ctx, actor_type="MERCHANT"),
                properties={
                    "status": "failed",
                    "result_count": 0,
                    "reason_code": "embedding_failed",
                    "provider_code": getattr(provider, "code", ""),
                },
            )
            return SearchResult(
                results=[],
                provider=getattr(provider, "code", ""),
                warnings=["fallback_used"],
                fallback_reason="embedding_failed",
            )


@transaction.atomic
def _ensure_embeddings(store_id: int, provider_code: str, limit: int = 100) -> None:
    existing_ids = set(
        AIProductEmbedding.objects.filter(store_id=store_id).values_list("product_id", flat=True)
    )
    products = (
        Product.objects.filter(store_id=store_id, image__isnull=False)
        .exclude(id__in=existing_ids)
        .order_by("-id")[:limit]
    )
    for product in products:
        try:
            if not product.image:
                continue
            with default_storage.open(product.image.name, "rb") as handle:
                image_bytes = handle.read()
            provider = get_provider()
            vector = provider.embed_image(image_bytes=image_bytes).vector
            upsert_embedding(store_id=store_id, product_id=product.id, vector=vector, provider=provider_code)
        except Exception:
            continue
