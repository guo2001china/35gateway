from __future__ import annotations

from decimal import ROUND_UP, Decimal
from typing import Any

from app.core.config import settings

CNY = "CNY"
ZERO = Decimal("0")
LAST_VERIFIED_AT = "2026-03-26"
USD_TO_CNY_FIXED = Decimal("7")
TARGET_GROSS_MARGIN = Decimal("0.10")
DEFAULT_MODEL_MULTIPLIER = Decimal("1.11111111")


def decimal_value(value: str) -> Decimal:
    return Decimal(value)


def usd_to_cny(value: str | Decimal, *, precision: Decimal = Decimal("0.00000001")) -> Decimal:
    return (Decimal(str(value)) * USD_TO_CNY_FIXED).quantize(precision)


def usd_price_fields_to_cny(
    price_fields: dict[str, str],
    *,
    precision: Decimal = Decimal("0.000000000001"),
) -> dict[str, str]:
    return {
        key: str(usd_to_cny(value, precision=precision))
        for key, value in price_fields.items()
    }


def sale_price_for_target_margin(
    cost_unit_price: Decimal,
    *,
    gross_margin: Decimal = TARGET_GROSS_MARGIN,
    precision: Decimal = Decimal("0.00000001"),
) -> Decimal:
    if cost_unit_price <= ZERO:
        return ZERO
    if gross_margin <= ZERO:
        return cost_unit_price.quantize(precision)
    if gross_margin >= Decimal("1"):
        raise ValueError("gross_margin_must_be_less_than_1")
    sale_price = cost_unit_price / (Decimal("1") - gross_margin)
    return sale_price.quantize(precision, rounding=ROUND_UP)


def sale_price_for_multiplier(
    cost_unit_price: Decimal,
    *,
    multiplier: Decimal = DEFAULT_MODEL_MULTIPLIER,
    precision: Decimal = Decimal("0.00000001"),
) -> Decimal:
    if cost_unit_price <= ZERO:
        return ZERO
    if multiplier <= ZERO:
        return ZERO
    return (cost_unit_price * multiplier).quantize(precision, rounding=ROUND_UP)


def apply_multiplier_to_price_fields(
    price_fields: dict[str, Any],
    *,
    multiplier: Decimal = DEFAULT_MODEL_MULTIPLIER,
    precision: Decimal = Decimal("0.00000001"),
) -> dict[str, str]:
    derived: dict[str, str] = {}
    for key, raw_value in dict(price_fields or {}).items():
        text = str(raw_value)
        if "~" in text:
            parts: list[str] = []
            for part in text.split("~", 1):
                try:
                    numeric = Decimal(part.strip())
                except Exception:
                    parts = []
                    break
                parts.append(str(sale_price_for_multiplier(numeric, multiplier=multiplier, precision=precision)))
            if parts:
                derived[key] = "~".join(parts)
            continue
        try:
            numeric = Decimal(text)
        except Exception:
            continue
        derived[key] = str(sale_price_for_multiplier(numeric, multiplier=multiplier, precision=precision))
    return derived


def derive_multiplier_from_price_fields(
    *,
    sale_price_fields: dict[str, Any],
    cost_price_fields: dict[str, Any],
) -> Decimal | None:
    for key, raw_sale in dict(sale_price_fields or {}).items():
        if key not in dict(cost_price_fields or {}):
            continue
        try:
            sale_value = Decimal(str(raw_sale))
            cost_value = Decimal(str(cost_price_fields[key]))
        except Exception:
            continue
        if cost_value <= ZERO:
            continue
        return (sale_value / cost_value).quantize(Decimal("0.00000001"))
    return None


def gross_margin_ratio(*, sale_amount: Decimal, cost_amount: Decimal) -> Decimal | None:
    if sale_amount <= ZERO:
        return None
    return ((sale_amount - cost_amount) / sale_amount).quantize(Decimal("0.0001"))


def margin_summary(
    *,
    sale_unit_price: str | None,
    cost_unit_price: str | None,
    billing_unit: str,
) -> dict[str, Any]:
    if sale_unit_price is None or cost_unit_price is None:
        return {
            "billing_unit": billing_unit,
            "status": "not_applicable",
        }
    sale = decimal_value(sale_unit_price)
    cost = decimal_value(cost_unit_price)
    gross_margin = gross_margin_ratio(sale_amount=sale, cost_amount=cost)
    return {
        "billing_unit": billing_unit,
        "status": "computed",
        "sale_unit_price": str(sale),
        "cost_unit_price": str(cost),
        "margin_per_unit": str(sale - cost),
        "gross_margin_ratio": None if gross_margin is None else str(gross_margin),
    }


def power_unit_price(unit_price: Decimal) -> Decimal:
    return unit_price * Decimal(settings.power_rate_cny)


def extract_seconds(payload: dict[str, Any]) -> int | None:
    value = payload.get("seconds", payload.get("duration"))
    if value is None:
        return None
    if isinstance(value, str) and value.endswith("s"):
        value = value[:-1]
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_image_resolution_key(payload: dict[str, Any]) -> str:
    resolution = str(payload.get("resolution") or "1K").upper()
    if resolution in {"512", "1K", "2K", "4K"}:
        return resolution
    return "1K"


def extract_image_count(payload: dict[str, Any]) -> int:
    value = payload.get("num_images", 1)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(parsed, 4))


def extract_input_image_count(payload: dict[str, Any]) -> int:
    image_urls = payload.get("image_urls") or payload.get("input_images") or []
    if isinstance(image_urls, list):
        return len([item for item in image_urls if item])
    return 0


def extract_veo_resolution_key(payload: dict[str, Any]) -> str:
    resolution = str(payload.get("resolution") or "720p").lower()
    if resolution == "4k":
        return "4k"
    return "default"


def empty_snapshot(
    *,
    provider_code: str,
    route_group: str,
    model_code: str,
    billing_unit: str,
) -> dict[str, Any]:
    return {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {},
        "user_price": {"currency": CNY, "unit_price": "0"},
        "provider_cost": {"currency": CNY, "unit_price": "0"},
        "sale_amount": "0",
        "sale_currency": CNY,
        "cost_amount": "0",
        "cost_currency": CNY,
        "margin_amount": "0",
        "power_unit_price": "0",
        "power_amount": "0",
        "quoted_amount": "0",
        "quoted_currency": CNY,
    }
