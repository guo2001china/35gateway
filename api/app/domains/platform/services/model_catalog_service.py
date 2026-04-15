from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.provider_catalog import get_provider
from app.domains.platform.services.provider_metrics import ProviderMetricsService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.public_model_pricing import build_public_model_price_lines


@dataclass(frozen=True)
class ProviderOffering:
    public_model_code: str
    execution_model_code: str
    metrics_model_code: str
    route_group: str
    provider_code: str
    provider_name: str
    lane: str
    billing_unit: str
    is_async: bool
    is_streaming: bool


class ModelCatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = ProviderMetricsService(db)

    def _snapshot(self):
        return get_platform_config_snapshot()

    def _get_model_or_404(self, model_code: str):
        try:
            return self._snapshot().get_model(model_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="model_not_found") from exc

    def _primary_route_or_404(self, model_code: str):
        route = self._snapshot().get_primary_route(model_code)
        if route is None:
            raise HTTPException(status_code=404, detail="model_not_found")
        return route

    def _pricing_for_model(self, model_code: str) -> dict[str, Any]:
        pricing = self._snapshot().get_pricing_for_model(model_code)
        if pricing is None:
            return {}
        sale_price = dict(pricing.sale_price_fields or {})
        return {
            "currency": pricing.currency,
            "source_url": pricing.source_url,
            "billing_unit": pricing.billing_unit,
            "price_lines": build_public_model_price_lines(
                category=self._get_model_or_404(model_code).category,
                billing_unit=pricing.billing_unit,
                currency=pricing.currency,
                sale_price=sale_price,
            ),
        }

    def _providers_for_route(self, model_code: str, route_group: str) -> list[ProviderOffering]:
        route = self._snapshot().get_route(model_code, route_group)
        providers: list[ProviderOffering] = []
        for binding in self._snapshot().list_bindings(model_code, route_group):
            try:
                provider = get_provider(binding.provider_code)
            except KeyError:
                continue
            providers.append(
                ProviderOffering(
                    public_model_code=model_code,
                    execution_model_code=binding.execution_model_code,
                    metrics_model_code=binding.execution_model_code,
                    route_group=route_group,
                    provider_code=provider.provider_code,
                    provider_name=provider.provider_name,
                    lane=provider.lane,
                    billing_unit=self._get_model_or_404(model_code).billing_unit,
                    is_async=binding.is_async,
                    is_streaming=binding.is_streaming,
                )
            )
        configured_order = {
            provider_code: index
            for index, provider_code in enumerate(route.default_chain)
        }
        providers.sort(
            key=lambda item: (
                configured_order.get(item.provider_code, len(configured_order)),
                item.provider_code,
            )
        )
        return providers

    def _provider_metrics_for_model(
        self,
        providers: list[ProviderOffering],
        window: str,
    ) -> dict[str, dict[str, Any]]:
        effective_window = self.metrics_service.parse_window(window)
        metrics_by_provider: dict[str, dict[str, Any]] = {}
        metrics_codes = {provider.metrics_model_code for provider in providers}
        for metrics_model_code in metrics_codes:
            provider_metrics = self.metrics_service.provider_metrics(metrics_model_code, effective_window)
            for provider_code, metrics in provider_metrics.items():
                metrics_by_provider.setdefault(provider_code, metrics)
        for provider in providers:
            metrics_by_provider.setdefault(provider.provider_code, self.metrics_service.default_metrics(effective_window))
        if not providers:
            return {}
        return metrics_by_provider

    def _serialize_provider(
        self,
        provider: ProviderOffering,
        *,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "provider_code": provider.provider_code,
            "provider_name": provider.provider_name,
            "lane": provider.lane,
            "billing_unit": provider.billing_unit,
            "is_async": provider.is_async,
            "is_streaming": provider.is_streaming,
            "route_group": provider.route_group,
            "execution_model_code": provider.execution_model_code,
            "metrics": metrics,
        }

    def list_models(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for model in self._snapshot().list_public_models():
            route = self._primary_route_or_404(model.public_model_code)
            provider_count = len(self._providers_for_route(model.public_model_code, route.route_group))
            if provider_count == 0:
                continue
            pricing = self._pricing_for_model(model.public_model_code)
            items.append(
                {
                    "model_code": model.public_model_code,
                    "display_name": model.display_name,
                    "status": model.status,
                    "category": model.category,
                    "summary": model.summary,
                    "create_endpoint": route.endpoints.get("create"),
                    "pricing": {
                        "currency": pricing.get("currency"),
                        "billing_unit": pricing.get("billing_unit"),
                        "price_lines": pricing.get("price_lines") or [],
                    },
                    "provider_count": provider_count,
                }
            )
        return items

    def get_model_detail(self, model_code: str, window: str = "24h") -> dict[str, Any]:
        model = self._get_model_or_404(model_code)
        route = self._primary_route_or_404(model_code)
        pricing = self._pricing_for_model(model_code)
        base_providers = self._providers_for_route(model_code, route.route_group)
        metrics_by_provider = self._provider_metrics_for_model(base_providers, window)
        providers = [
            self._serialize_provider(
                provider,
                metrics=metrics_by_provider.get(provider.provider_code),
            )
            for provider in base_providers
        ]
        return {
            "model_code": model_code,
            "display_name": model.display_name,
            "status": model.status,
            "route_group": route.route_group,
            "category": model.category,
            "summary": model.summary,
            "supported_input_modes": list(route.supported_input_modes),
            "endpoints": route.endpoints,
            "api_doc": route.api_doc,
            "docs_url": model.docs_url,
            "pricing": {
                "currency": pricing.get("currency"),
                "source_url": pricing.get("source_url"),
                "billing_unit": pricing.get("billing_unit"),
                "price_lines": pricing.get("price_lines") or [],
            },
            "routes": [
                {
                    "route_group": item.route_group,
                    "endpoints": item.endpoints,
                    "api_doc": item.api_doc,
                    "supported_input_modes": list(item.supported_input_modes),
                    "public_api_visible": item.public_api_visible,
                    "is_primary": item.is_primary,
                }
                for item in self._snapshot().list_routes(model_code, public_only=False)
            ],
            "providers": providers,
        }

    def list_model_providers(self, model_code: str, window: str = "24h") -> list[dict[str, Any]]:
        route = self._primary_route_or_404(model_code)
        providers = self._providers_for_route(model_code, route.route_group)
        metrics_by_provider = self._provider_metrics_for_model(providers, window)
        return [
            self._serialize_provider(provider, metrics=metrics_by_provider.get(provider.provider_code))
            for provider in providers
        ]
