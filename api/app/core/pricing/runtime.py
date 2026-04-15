from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.pricing.common import (
    DEFAULT_MODEL_MULTIPLIER,
    apply_multiplier_to_price_fields,
    sale_price_for_multiplier,
)
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot


def get_model_multiplier(model_code: str) -> Decimal:
    snapshot = get_platform_config_snapshot()
    pricing = snapshot.get_pricing_for_model(model_code)
    if pricing is None or pricing.multiplier is None:
        return DEFAULT_MODEL_MULTIPLIER
    return pricing.multiplier


def sale_price_for_model_multiplier(
    *,
    model_code: str,
    cost_unit_price: Decimal,
    precision: Decimal = Decimal("0.00000001"),
) -> Decimal:
    return sale_price_for_multiplier(
        cost_unit_price,
        multiplier=get_model_multiplier(model_code),
        precision=precision,
    )


def sale_price_for_model(
    *,
    model_code: str,
    cost_unit_price: Decimal,
    precision: Decimal = Decimal("0.00000001"),
) -> Decimal:
    return sale_price_for_model_multiplier(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=precision,
    )


def sale_price_fields_for_model_multiplier(
    *,
    model_code: str,
    cost_price_fields: dict[str, Any],
    precision: Decimal = Decimal("0.00000001"),
) -> dict[str, str]:
    return apply_multiplier_to_price_fields(
        cost_price_fields,
        multiplier=get_model_multiplier(model_code),
        precision=precision,
    )


def sale_price_fields_for_model(
    *,
    model_code: str,
    cost_price_fields: dict[str, Any],
    precision: Decimal = Decimal("0.00000001"),
) -> dict[str, str]:
    return sale_price_fields_for_model_multiplier(
        model_code=model_code,
        cost_price_fields=cost_price_fields,
        precision=precision,
    )
