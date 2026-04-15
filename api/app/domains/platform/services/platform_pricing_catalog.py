from __future__ import annotations

from typing import Any

from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot


def list_platform_pricing_catalog_items() -> list[dict[str, Any]]:
    snapshot = get_platform_config_snapshot()
    items: list[dict[str, Any]] = []

    for model in sorted(
        snapshot.models.values(),
        key=lambda item: (item.category, item.display_name.lower(), item.public_model_code),
    ):
        pricing = snapshot.get_pricing_for_model(model.public_model_code)
        if pricing is None:
            continue
        for route in snapshot.list_routes(model.public_model_code):
            endpoint = route.endpoints.get("create") if isinstance(route.endpoints, dict) else None
            items.append(
                {
                    "route_group": route.route_group,
                    "endpoint": endpoint,
                    "model_code": model.public_model_code,
                    "billing_unit": pricing.billing_unit,
                    "currency": pricing.currency,
                    "official_price": pricing.official_price,
                    "sale_price_fields": pricing.sale_price_fields,
                    "provider_cost": pricing.provider_cost,
                    "margin_snapshot": pricing.margin_snapshot,
                    "notes": pricing.notes,
                    "source_url": pricing.source_url,
                    "last_verified_at": (
                        pricing.last_verified_at.date().isoformat()
                        if pricing.last_verified_at is not None
                        else None
                    ),
                }
            )
    return items
