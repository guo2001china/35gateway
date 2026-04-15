from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from app.core.pricing.common import CNY, decimal_value, power_unit_price
from app.core.pricing.runtime import sale_price_fields_for_model
from app.core.pricing.text_cost_specs import DEFAULT_PROVIDER, get_text_cost_spec
from app.core.pricing.text_usage import TextUsage, estimate_text_usage, parse_text_usage_from_response

ONE_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class MoneyQuote:
    amount: Decimal
    currency: str
    price_fields: dict[str, str]
    rule_code: str


@dataclass(frozen=True)
class TextSettlement:
    usage: TextUsage
    sale: MoneyQuote
    cost: MoneyQuote

    @property
    def power_amount(self) -> Decimal:
        return power_unit_price(self.sale.amount)

    @property
    def margin_amount(self) -> Decimal:
        return self.sale.amount - self.cost.amount


class BaseTextCalculator:
    model_code: str
    route_groups: tuple[str, ...]

    def supports(self, *, route_group: str, model_code: str) -> bool:
        return self.model_code == model_code and route_group in self.route_groups

    def estimate(
        self,
        *,
        provider_code: str,
        route_group: str,
        payload: dict[str, object],
        sale_model_code: str | None = None,
    ) -> TextSettlement:
        usage = estimate_text_usage(route_group=route_group, payload=payload)
        return self._settlement(provider_code=provider_code, usage=usage, sale_model_code=sale_model_code)

    def settle(
        self,
        *,
        provider_code: str,
        route_group: str,
        response_payload: dict[str, object],
        sale_model_code: str | None = None,
    ) -> TextSettlement | None:
        usage = parse_text_usage_from_response(route_group=route_group, response_payload=response_payload)
        if usage is None:
            return None
        return self._settlement(provider_code=provider_code, usage=usage, sale_model_code=sale_model_code)

    def _settlement(self, *, provider_code: str, usage: TextUsage, sale_model_code: str | None = None) -> TextSettlement:
        return TextSettlement(
            usage=usage,
            sale=self._quote_sale(usage, sale_model_code=sale_model_code),
            cost=self._quote_cost(provider_code=provider_code, usage=usage),
        )

    def _quote_sale(self, usage: TextUsage, *, sale_model_code: str | None = None) -> MoneyQuote:
        raise NotImplementedError

    def _quote_cost(self, *, provider_code: str, usage: TextUsage) -> MoneyQuote:
        raise NotImplementedError


class CachedTokenCalculator(BaseTextCalculator):
    def __init__(self, *, model_code: str, route_groups: tuple[str, ...], sale_rule_fallback: str, cost_rule_fallback: str):
        self.model_code = model_code
        self.route_groups = route_groups
        self.sale_rule_fallback = sale_rule_fallback
        self.cost_rule_fallback = cost_rule_fallback

    def _quote_sale(self, usage: TextUsage, *, sale_model_code: str | None = None) -> MoneyQuote:
        cost_spec = get_text_cost_spec(DEFAULT_PROVIDER, self.model_code) or {}
        cost_price_fields = dict(cost_spec.get("price_fields") or {})
        price_fields = sale_price_fields_for_model(
            model_code=sale_model_code or self.model_code,
            cost_price_fields=cost_price_fields,
        )
        amount = _cached_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=self.sale_rule_fallback,
        )

    def _quote_cost(self, *, provider_code: str, usage: TextUsage) -> MoneyQuote:
        spec = get_text_cost_spec(provider_code, self.model_code) or {}
        price_fields = dict(spec.get("price_fields") or {})
        amount = _cached_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=str(spec.get("rule_code") or self.cost_rule_fallback),
        )


class FlatTokenCalculator(BaseTextCalculator):
    def __init__(self, *, model_code: str, route_groups: tuple[str, ...], sale_rule_fallback: str, cost_rule_fallback: str):
        self.model_code = model_code
        self.route_groups = route_groups
        self.sale_rule_fallback = sale_rule_fallback
        self.cost_rule_fallback = cost_rule_fallback

    def _quote_sale(self, usage: TextUsage, *, sale_model_code: str | None = None) -> MoneyQuote:
        cost_spec = get_text_cost_spec(DEFAULT_PROVIDER, self.model_code) or {}
        cost_price_fields = dict(cost_spec.get("price_fields") or {})
        price_fields = sale_price_fields_for_model(
            model_code=sale_model_code or self.model_code,
            cost_price_fields=cost_price_fields,
        )
        amount = _flat_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=self.sale_rule_fallback,
        )

    def _quote_cost(self, *, provider_code: str, usage: TextUsage) -> MoneyQuote:
        spec = get_text_cost_spec(provider_code, self.model_code) or {}
        price_fields = dict(spec.get("price_fields") or {})
        amount = _flat_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=str(spec.get("rule_code") or self.cost_rule_fallback),
        )


class DeepSeekCachedTokenCalculator(BaseTextCalculator):
    def __init__(self, *, model_code: str, route_groups: tuple[str, ...], sale_rule_fallback: str, cost_rule_fallback: str):
        self.model_code = model_code
        self.route_groups = route_groups
        self.sale_rule_fallback = sale_rule_fallback
        self.cost_rule_fallback = cost_rule_fallback

    def _quote_sale(self, usage: TextUsage, *, sale_model_code: str | None = None) -> MoneyQuote:
        cost_spec = get_text_cost_spec(DEFAULT_PROVIDER, self.model_code) or {}
        cost_price_fields = dict(cost_spec.get("price_fields") or {})
        price_fields = sale_price_fields_for_model(
            model_code=sale_model_code or self.model_code,
            cost_price_fields=cost_price_fields,
        )
        amount = _deepseek_cached_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=self.sale_rule_fallback,
        )

    def _quote_cost(self, *, provider_code: str, usage: TextUsage) -> MoneyQuote:
        spec = get_text_cost_spec(provider_code, self.model_code) or {}
        price_fields = dict(spec.get("price_fields") or {})
        amount = _deepseek_cached_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=str(spec.get("rule_code") or self.cost_rule_fallback),
        )


class InputTieredTokenCalculator(BaseTextCalculator):
    def __init__(self, *, model_code: str, route_groups: tuple[str, ...], sale_rule_fallback: str, cost_rule_fallback: str):
        self.model_code = model_code
        self.route_groups = route_groups
        self.sale_rule_fallback = sale_rule_fallback
        self.cost_rule_fallback = cost_rule_fallback

    def _settlement(self, *, provider_code: str, usage: TextUsage, sale_model_code: str | None = None) -> TextSettlement:
        usage = replace(
            usage,
            pricing_tier="gt_200k" if usage.input_tokens > 200000 else "lte_200k",
        )
        return super()._settlement(provider_code=provider_code, usage=usage, sale_model_code=sale_model_code)

    def _quote_sale(self, usage: TextUsage, *, sale_model_code: str | None = None) -> MoneyQuote:
        cost_spec = get_text_cost_spec(DEFAULT_PROVIDER, self.model_code) or {}
        cost_price_fields = dict(cost_spec.get("price_fields") or {})
        price_fields = sale_price_fields_for_model(
            model_code=sale_model_code or self.model_code,
            cost_price_fields=cost_price_fields,
        )
        amount = _tiered_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=self.sale_rule_fallback,
        )

    def _quote_cost(self, *, provider_code: str, usage: TextUsage) -> MoneyQuote:
        spec = get_text_cost_spec(provider_code, self.model_code) or {}
        price_fields = dict(spec.get("price_fields") or {})
        amount = _tiered_amount(price_fields=price_fields, usage=usage)
        return MoneyQuote(
            amount=amount,
            currency=CNY,
            price_fields=price_fields,
            rule_code=str(spec.get("rule_code") or self.cost_rule_fallback),
        )


def _decimal_field(price_fields: dict[str, str], field: str) -> Decimal:
    return decimal_value(str(price_fields.get(field) or "0"))


def _cached_amount(*, price_fields: dict[str, str], usage: TextUsage) -> Decimal:
    billable_input_tokens = max(0, usage.input_tokens - usage.cached_input_tokens)
    input_price = _decimal_field(price_fields, "input_per_1m_tokens")
    cached_input_price = _decimal_field(price_fields, "cached_input_per_1m_tokens")
    output_price = _decimal_field(price_fields, "output_per_1m_tokens")
    return (
        input_price * Decimal(billable_input_tokens)
        + cached_input_price * Decimal(usage.cached_input_tokens)
        + output_price * Decimal(usage.output_tokens)
    ) / ONE_MILLION


def _flat_amount(*, price_fields: dict[str, str], usage: TextUsage) -> Decimal:
    input_price = _decimal_field(price_fields, "input_per_1m_tokens")
    output_price = _decimal_field(price_fields, "output_per_1m_tokens")
    return (input_price * Decimal(usage.input_tokens) + output_price * Decimal(usage.output_tokens)) / ONE_MILLION


def _tiered_amount(*, price_fields: dict[str, str], usage: TextUsage) -> Decimal:
    suffix = "gt_200k" if usage.input_tokens > 200000 else "lte_200k"
    input_price = _decimal_field(price_fields, f"input_per_1m_tokens_{suffix}")
    cached_input_price = _decimal_field(price_fields, f"cached_input_per_1m_tokens_{suffix}")
    output_price = _decimal_field(price_fields, f"output_per_1m_tokens_{suffix}")
    billable_input_tokens = max(0, usage.input_tokens - usage.cached_input_tokens)
    return (
        input_price * Decimal(billable_input_tokens)
        + cached_input_price * Decimal(usage.cached_input_tokens)
        + output_price * Decimal(usage.output_tokens)
    ) / ONE_MILLION


def _deepseek_cached_amount(*, price_fields: dict[str, str], usage: TextUsage) -> Decimal:
    billable_input_tokens = max(0, usage.input_tokens - usage.cached_input_tokens)
    cache_hit_price = _decimal_field(price_fields, "cache_hit_input_per_1m_tokens")
    cache_miss_price = _decimal_field(price_fields, "cache_miss_input_per_1m_tokens")
    output_price = _decimal_field(price_fields, "output_per_1m_tokens")
    return (
        cache_miss_price * Decimal(billable_input_tokens)
        + cache_hit_price * Decimal(usage.cached_input_tokens)
        + output_price * Decimal(usage.output_tokens)
    ) / ONE_MILLION


TEXT_CALCULATORS: tuple[BaseTextCalculator, ...] = (
    CachedTokenCalculator(
        model_code="gpt-5",
        route_groups=("openai",),
        sale_rule_fallback="text.gpt_5.cached_tokens",
        cost_rule_fallback="cost.text.gpt_5.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gpt-5.2",
        route_groups=("openai",),
        sale_rule_fallback="text.gpt_5_2.cached_tokens",
        cost_rule_fallback="cost.text.gpt_5_2.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gpt-5.4",
        route_groups=("openai", "responses"),
        sale_rule_fallback="text.gpt_5_4.cached_tokens",
        cost_rule_fallback="cost.text.gpt_5_4.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gpt-5.4-mini",
        route_groups=("openai", "responses"),
        sale_rule_fallback="text.gpt_5_4_mini.cached_tokens",
        cost_rule_fallback="cost.text.gpt_5_4_mini.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gpt-5.4-nano",
        route_groups=("openai", "responses"),
        sale_rule_fallback="text.gpt_5_4_nano.cached_tokens",
        cost_rule_fallback="cost.text.gpt_5_4_nano.cached_tokens",
    ),
    FlatTokenCalculator(
        model_code="gpt-5.4-pro",
        route_groups=("responses",),
        sale_rule_fallback="text.gpt_5_4_pro.flat_tokens",
        cost_rule_fallback="cost.text.gpt_5_4_pro.flat_tokens",
    ),
    DeepSeekCachedTokenCalculator(
        model_code="DeepSeek-V3.2",
        route_groups=("openai",),
        sale_rule_fallback="text.deepseek_v3_2.cached_tokens",
        cost_rule_fallback="cost.text.deepseek_v3_2.cached_tokens",
    ),
    InputTieredTokenCalculator(
        model_code="gemini-2.5-pro",
        route_groups=("openai", "gemini"),
        sale_rule_fallback="text.gemini_2_5_pro.input_tiered",
        cost_rule_fallback="cost.text.gemini_2_5_pro.input_tiered",
    ),
    CachedTokenCalculator(
        model_code="gemini-2.5-flash",
        route_groups=("openai",),
        sale_rule_fallback="text.gemini_flat.cached_tokens",
        cost_rule_fallback="cost.text.gemini_flat.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gemini-2.5-flash-lite",
        route_groups=("openai",),
        sale_rule_fallback="text.gemini_flat.cached_tokens",
        cost_rule_fallback="cost.text.gemini_flat.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="gemini-3-flash-preview",
        route_groups=("openai",),
        sale_rule_fallback="text.gemini_flat.cached_tokens",
        cost_rule_fallback="cost.text.gemini_flat.cached_tokens",
    ),
    InputTieredTokenCalculator(
        model_code="gemini-3.1-pro-preview",
        route_groups=("openai",),
        sale_rule_fallback="text.gemini_3_1_pro.input_tiered",
        cost_rule_fallback="cost.text.gemini_3_1_pro.input_tiered",
    ),
    CachedTokenCalculator(
        model_code="gemini-3.1-flash-lite-preview",
        route_groups=("openai",),
        sale_rule_fallback="text.gemini_flat.cached_tokens",
        cost_rule_fallback="cost.text.gemini_flat.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="MiniMax-M2.7",
        route_groups=("openai",),
        sale_rule_fallback="text.minimax_m2_7.cached_tokens",
        cost_rule_fallback="cost.text.minimax_m2_7.cached_tokens",
    ),
    CachedTokenCalculator(
        model_code="MiniMax-M2.7-highspeed",
        route_groups=("openai",),
        sale_rule_fallback="text.minimax_m2_7_highspeed.cached_tokens",
        cost_rule_fallback="cost.text.minimax_m2_7_highspeed.cached_tokens",
    ),
    FlatTokenCalculator(
        model_code="glm-4.7-flash",
        route_groups=("openai",),
        sale_rule_fallback="text.cloudflare.flat_tokens",
        cost_rule_fallback="cost.text.cloudflare.flat_tokens",
    ),
    FlatTokenCalculator(
        model_code="openrouter-free",
        route_groups=("openai",),
        sale_rule_fallback="text.openrouter.zero_cost",
        cost_rule_fallback="cost.text.openrouter.zero_cost",
    ),
    FlatTokenCalculator(
        model_code="step-3.5-flash",
        route_groups=("openai",),
        sale_rule_fallback="text.openrouter.zero_cost",
        cost_rule_fallback="cost.text.openrouter.zero_cost",
    ),
)


def get_text_calculator(*, route_group: str, model_code: str) -> BaseTextCalculator | None:
    for calculator in TEXT_CALCULATORS:
        if calculator.supports(route_group=route_group, model_code=model_code):
            return calculator
    return None


def quote_text_settlement(
    *,
    provider_code: str,
    route_group: str,
    model_code: str,
    payload: dict[str, object],
    sale_model_code: str | None = None,
) -> TextSettlement | None:
    calculator = get_text_calculator(route_group=route_group, model_code=model_code)
    if calculator is None:
        return None
    return calculator.estimate(
        provider_code=provider_code,
        route_group=route_group,
        payload=payload,
        sale_model_code=sale_model_code,
    )


def finalize_text_settlement(
    *,
    provider_code: str,
    route_group: str,
    model_code: str,
    response_payload: dict[str, object],
    sale_model_code: str | None = None,
) -> TextSettlement | None:
    calculator = get_text_calculator(route_group=route_group, model_code=model_code)
    if calculator is None:
        return None
    return calculator.settle(
        provider_code=provider_code,
        route_group=route_group,
        response_payload=response_payload,
        sale_model_code=sale_model_code,
    )
