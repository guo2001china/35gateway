from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.pricing_catalog import quote_request
from app.domains.platform.services.provider_metrics import ProviderMetricsService
from app.domains.platform.services.routing import RouteResult


class ProviderOptionsService:
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = ProviderMetricsService(db)

    def build_provider_options(
        self,
        *,
        route_group: str,
        public_model_code: str,
        request_payload: dict[str, Any],
        attempts: list[RouteResult],
        provider_lookup,
        window: str,
    ) -> list[dict[str, Any]]:
        effective_window = self.metrics_service.parse_window(window)
        metrics_map = self.metrics_service.provider_metrics_for_model_codes(
            [attempt.execution_model_code for attempt in attempts],
            effective_window,
        )
        options: list[dict[str, Any]] = []
        for attempt_no, route_result in enumerate(attempts, start=1):
            provider = route_result.provider or provider_lookup(route_result.provider_code)
            amount, currency, billing_snapshot = quote_request(
                provider_code=route_result.provider_code,
                route_group=route_group,
                execution_model_code=route_result.execution_model_code,
                pricing_strategy=route_result.pricing_strategy,
                public_model_code=public_model_code,
                payload=request_payload,
            )
            metrics = metrics_map.get(
                route_result.provider_code,
                self.metrics_service.default_metrics(effective_window),
            )
            options.append(
                {
                    "attempt_no": attempt_no,
                    "provider_code": provider.provider_code,
                    "provider_name": provider.provider_name,
                    "provider_account_short_id": route_result.provider_account_short_id,
                    "provider_account_owner_type": route_result.provider_account_owner_type,
                    "model_code": route_result.execution_model_code,
                    "execution_model_code": route_result.execution_model_code,
                    "pricing_strategy": route_result.pricing_strategy,
                    "billing_unit": billing_snapshot.get("billing_unit"),
                    "estimated_amount": str(amount),
                    "estimated_power_amount": billing_snapshot.get("power_amount"),
                    "currency": currency,
                    "pricing_snapshot": billing_snapshot,
                    "metrics": metrics,
                }
            )

        for index, option in enumerate(options, start=1):
            option["rank"] = index
            option["recommended"] = index == 1
        return self.normalize_provider_options(options)

    def normalize_provider_options(self, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            options,
            key=lambda item: (
                int(item.get("attempt_no") or 10**9),
                str(item.get("provider_code") or ""),
            ),
        )
