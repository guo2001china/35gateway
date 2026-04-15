from __future__ import annotations

from typing import Any

from app.api.schemas.common import OpenSchemaModel


class PriceSnapshot(OpenSchemaModel):
    currency: str | None = None
    billing_unit: str | None = None
    price_lines: list[dict[str, str]] = []


class ProviderMetricsLatency(OpenSchemaModel):
    avg_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    sample_count: int = 0


class ProviderMetrics(OpenSchemaModel):
    window: str
    sample_count: int = 0
    success_count: int = 0
    success_rate: float | None = None
    sample_ready: bool = False
    latency: ProviderMetricsLatency


class ProviderCatalogItem(OpenSchemaModel):
    provider_code: str
    provider_name: str
    lane: str
    billing_unit: str
    is_async: bool
    is_streaming: bool
    metrics: ProviderMetrics | None = None


class ModelListPricing(OpenSchemaModel):
    currency: str | None = None
    billing_unit: str | None = None
    price_lines: list[dict[str, str]] = []


class ModelListItem(OpenSchemaModel):
    model_code: str
    display_name: str
    status: str
    category: str
    summary: str
    create_endpoint: str | None = None
    pricing: ModelListPricing
    provider_count: int


class ModelDetailPricing(OpenSchemaModel):
    currency: str | None = None
    source_url: str | None = None
    billing_unit: str | None = None
    price_lines: list[dict[str, str]] = []


class ModelDetailResponse(OpenSchemaModel):
    model_code: str
    display_name: str
    status: str
    route_group: str
    category: str
    summary: str
    supported_input_modes: list[str]
    endpoints: dict[str, Any]
    api_doc: dict[str, Any]
    docs_url: str | None = None
    pricing: ModelDetailPricing
    providers: list[ProviderCatalogItem]
