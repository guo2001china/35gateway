from __future__ import annotations

from decimal import ROUND_HALF_UP, ROUND_UP
from decimal import Decimal
from typing import Any

from app.core.pricing.common import CNY, LAST_VERIFIED_AT, ZERO, empty_snapshot, gross_margin_ratio, power_unit_price
from app.core.pricing.text_calculators import finalize_text_settlement, quote_text_settlement
from app.core.pricing.text_cost_specs import get_text_cost_spec
from app.core.pricing.text_sale_specs import TEXT_SALE_SPECS, get_text_sale_spec

TEXT_BILLING_ROUTES = {"openai", "responses", "gemini"}


def quote_text_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None = None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    settlement = quote_text_settlement(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        payload=payload,
        sale_model_code=model_code,
    )
    if settlement is None:
        return ZERO, CNY, empty_snapshot(
            provider_code=provider_code,
            route_group=route_group,
            model_code=model_code,
            billing_unit=billing_unit,
        )
    snapshot = _build_text_snapshot(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        billing_unit=billing_unit,
        settlement=settlement,
    )
    return Decimal(snapshot["quoted_amount"]), CNY, snapshot


def finalize_text_billing_snapshot(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None = None,
    billing_unit: str,
    response_payload: dict[str, Any],
    estimated_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    settlement = finalize_text_settlement(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        response_payload=response_payload,
        sale_model_code=model_code,
    )
    if settlement is None:
        return estimated_snapshot or empty_snapshot(
            provider_code=provider_code,
            route_group=route_group,
            model_code=model_code,
            billing_unit=billing_unit,
        )
    return _build_text_snapshot(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        billing_unit=billing_unit,
        settlement=settlement,
    )


def list_text_pricing_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for model_code in TEXT_SALE_SPECS.keys():
        spec = get_text_sale_spec(model_code) or {}
        catalog = dict(spec.get("catalog") or {})
        sale_fields = dict(spec.get("price_fields") or {})
        cost_spec = get_text_cost_spec("*", model_code) or {}
        cost_fields = dict(cost_spec.get("price_fields") or {})
        items.append(
            {
                "route_group": catalog.get("route_group"),
                "endpoint": catalog.get("endpoint"),
                "model_code": model_code,
                "billing_unit": "token",
                "currency": CNY,
                "official_price": dict(cost_fields),
                "sale_price_fields": dict(sale_fields),
                "provider_cost": dict(cost_fields),
                "margin_snapshot": {
                    "billing_unit": "token",
                    "status": "computed",
                    "sale_rule_code": spec.get("rule_code"),
                    "cost_rule_code": cost_spec.get("rule_code"),
                    "gross_margin_ratio": _derive_gross_margin_ratio(sale_fields=sale_fields, cost_fields=cost_fields),
                    "notes": catalog.get("margin_notes"),
                },
                "platform_billing_status": "quoted",
                "notes": catalog.get("notes"),
                "source_url": catalog.get("source_url"),
                "last_verified_at": LAST_VERIFIED_AT,
            }
        )
    return items


def _build_text_snapshot(
    *,
    provider_code: str,
    route_group: str,
    model_code: str,
    billing_unit: str,
    settlement,
) -> dict[str, Any]:
    usage = settlement.usage
    billable_input_tokens = max(0, usage.input_tokens - usage.cached_input_tokens)
    sale_amount = settlement.sale.amount.quantize(Decimal("0.00000001"), rounding=ROUND_UP)
    cost_amount = settlement.cost.amount.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    margin_amount = sale_amount - cost_amount
    power_amount = power_unit_price(sale_amount).quantize(Decimal("0.000001"), rounding=ROUND_UP)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": usage.cached_input_tokens,
            "billable_input_tokens": billable_input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "usage_source": usage.usage_source,
        },
        "user_price": {"currency": settlement.sale.currency, **settlement.sale.price_fields},
        "provider_cost": {"currency": settlement.cost.currency, **settlement.cost.price_fields},
        "sale_amount": str(sale_amount),
        "sale_currency": settlement.sale.currency,
        "cost_amount": str(cost_amount),
        "cost_currency": settlement.cost.currency,
        "margin_amount": str(margin_amount),
        "sale_rule_code": settlement.sale.rule_code,
        "cost_rule_code": settlement.cost.rule_code,
        "power_unit_price": "0",
        "power_amount": str(power_amount),
        "quoted_amount": str(sale_amount),
        "quoted_currency": settlement.sale.currency,
    }
    if usage.pricing_tier is not None:
        snapshot["request_factors"]["pricing_tier"] = usage.pricing_tier
    return snapshot


def _derive_gross_margin_ratio(*, sale_fields: dict[str, str], cost_fields: dict[str, str]) -> str | None:
    shared_keys = [key for key in sale_fields.keys() if key in cost_fields]
    if not shared_keys:
        return None
    key = shared_keys[0]
    sale_amount = Decimal(str(sale_fields[key]))
    cost_amount = Decimal(str(cost_fields[key]))
    ratio = gross_margin_ratio(sale_amount=sale_amount, cost_amount=cost_amount)
    if ratio is None:
        return None
    return str(ratio)
