from __future__ import annotations

from decimal import Decimal

from app.core.pricing.common import gross_margin_ratio
from app.core.pricing.quote import quote_request
from app.core.pricing.text import finalize_text_billing_snapshot
from app.core.pricing.text_calculators import get_text_calculator
from app.core.pricing.text_cost_specs import get_text_cost_spec
from app.core.pricing.text_sale_specs import get_text_sale_spec
from app.domains.platform.services.platform_bootstrap_source import build_platform_bootstrap


def _quote_text(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    public_model_code: str,
    payload: dict[str, object],
) -> tuple[Decimal, str, dict[str, object]]:
    return quote_request(
        provider_code=provider_code,
        route_group=route_group,
        execution_model_code=execution_model_code,
        pricing_strategy="text_tokens",
        public_model_code=public_model_code,
        payload=payload,
    )


def _finalize_text(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    public_model_code: str,
    response_payload: dict[str, object],
) -> dict[str, object]:
    return finalize_text_billing_snapshot(
        provider_code=provider_code,
        route_group=route_group,
        execution_model_code=execution_model_code,
        model_code=public_model_code,
        public_model_code=public_model_code,
        billing_unit="token",
        response_payload=response_payload,
        estimated_snapshot=None,
    )


def test_quote_request_estimates_gpt_54_tokens() -> None:
    amount, currency, snapshot = _quote_text(
        provider_code="openai_official",
        route_group="openai",
        execution_model_code="gpt-5.4",
        public_model_code="gpt-5.4",
        payload={
            "messages": [{"role": "user", "content": "hello world"}],
            "max_tokens": 64,
        },
    )

    assert currency == "CNY"
    assert amount > Decimal("0")
    assert snapshot["request_factors"]["usage_source"] == "estimated"
    assert snapshot["request_factors"]["output_tokens"] == 64
    assert snapshot["sale_rule_code"] == "text.gpt_5_4.cached_tokens"
    assert snapshot["cost_rule_code"] == "cost.text.gpt_5_4.cached_tokens"
    assert Decimal(snapshot["sale_amount"]) == amount
    assert Decimal(snapshot["margin_amount"]) > Decimal("0")


def test_quote_request_estimates_gpt_5_tokens() -> None:
    amount, currency, snapshot = _quote_text(
        provider_code="ksyun_openai",
        route_group="openai",
        execution_model_code="mog-1-global",
        public_model_code="gpt-5",
        payload={
            "messages": [{"role": "user", "content": "hello world"}],
            "max_tokens": 64,
        },
    )

    assert currency == "CNY"
    assert amount > Decimal("0")
    assert snapshot["sale_rule_code"] == "text.gpt_5.cached_tokens"
    assert snapshot["cost_rule_code"] == "cost.text.gpt_5.cached_tokens"


def test_finalize_text_billing_snapshot_uses_gpt_52_cached_token_pricing() -> None:
    snapshot = _finalize_text(
        provider_code="ksyun_openai",
        route_group="openai",
        execution_model_code="mog-2-global",
        public_model_code="gpt-5.2",
        response_payload={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "prompt_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.059045")
    assert snapshot["sale_rule_code"] == "text.gpt_5_2.cached_tokens"


def test_finalize_text_billing_snapshot_uses_openai_usage_with_cached_tokens() -> None:
    snapshot = _finalize_text(
        provider_code="openai_official",
        route_group="openai",
        execution_model_code="gpt-5.4",
        public_model_code="gpt-5.4",
        response_payload={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "prompt_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["usage_source"] == "provider_usage"
    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["quoted_amount"]) == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.06685")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert Decimal(snapshot["margin_amount"]) > Decimal("0")
    assert Decimal(snapshot["power_amount"]) > Decimal("0")


def test_finalize_text_billing_snapshot_uses_gpt_54_mini_cached_token_pricing() -> None:
    snapshot = _finalize_text(
        provider_code="openai_official",
        route_group="openai",
        execution_model_code="gpt-5.4-mini",
        public_model_code="gpt-5.4-mini",
        response_payload={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "prompt_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.020055")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert snapshot["sale_rule_code"] == "text.gpt_5_4_mini.cached_tokens"


def test_finalize_text_billing_snapshot_uses_gpt_54_nano_cached_token_pricing() -> None:
    snapshot = _finalize_text(
        provider_code="openai_official",
        route_group="openai",
        execution_model_code="gpt-5.4-nano",
        public_model_code="gpt-5.4-nano",
        response_payload={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "prompt_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.005523")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert snapshot["sale_rule_code"] == "text.gpt_5_4_nano.cached_tokens"


def test_finalize_text_billing_snapshot_uses_gpt_54_responses_usage_with_cached_tokens() -> None:
    snapshot = _finalize_text(
        provider_code="openai_official",
        route_group="responses",
        execution_model_code="gpt-5.4",
        public_model_code="gpt-5.4",
        response_payload={
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "input_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.06685")
    assert snapshot["sale_rule_code"] == "text.gpt_5_4.cached_tokens"


def test_finalize_text_billing_snapshot_uses_responses_usage() -> None:
    snapshot = _finalize_text(
        provider_code="openai_official",
        route_group="responses",
        execution_model_code="gpt-5.4-pro",
        public_model_code="gpt-5.4-pro",
        response_payload={
            "usage": {
                "input_tokens": 200,
                "output_tokens": 10,
                "total_tokens": 210,
            }
        }
    )

    assert snapshot["request_factors"]["input_tokens"] == 200
    assert snapshot["request_factors"]["output_tokens"] == 10
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.0546")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert snapshot["sale_rule_code"] == "text.gpt_5_4_pro.flat_tokens"


def test_finalize_text_billing_snapshot_uses_gemini_gt_200k_tier() -> None:
    snapshot = _finalize_text(
        provider_code="google_official",
        route_group="gemini",
        execution_model_code="gemini-2.5-pro",
        public_model_code="gemini-2.5-pro",
        response_payload={
            "usageMetadata": {
                "promptTokenCount": 210000,
                "candidatesTokenCount": 1000,
                "totalTokenCount": 211000,
            }
        }
    )

    assert snapshot["request_factors"]["pricing_tier"] == "gt_200k"
    assert Decimal(snapshot["cost_amount"]) == Decimal("3.78")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert snapshot["sale_rule_code"] == "text.gemini_2_5_pro.input_tiered"


def test_finalize_text_billing_snapshot_uses_deepseek_cached_input_pricing() -> None:
    snapshot = _finalize_text(
        provider_code="deepseek_official",
        route_group="openai",
        execution_model_code="DeepSeek-V3.2",
        public_model_code="DeepSeek-V3.2",
        response_payload={
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "prompt_tokens_details": {"cached_tokens": 200},
            }
        }
    )

    assert snapshot["request_factors"]["cached_input_tokens"] == 200
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.0030772")
    assert gross_margin_ratio(
        sale_amount=Decimal(snapshot["sale_amount"]),
        cost_amount=Decimal(snapshot["cost_amount"]),
    ) >= Decimal("0.10")
    assert snapshot["cost_rule_code"] == "cost.text.deepseek_v3_2.cached_tokens"


def test_all_public_text_models_have_sale_cost_specs_and_calculator() -> None:
    bootstrap = build_platform_bootstrap()
    models_by_code = {model.public_model_code: model for model in bootstrap.models}
    public_text_routes = [
        (route.public_model_code, route.route_group)
        for route in bootstrap.routes
        if models_by_code[route.public_model_code].category == "text"
        and models_by_code[route.public_model_code].status == "available"
        and route.public_api_visible
    ]

    missing_sale = [model_code for model_code, _ in public_text_routes if get_text_sale_spec(model_code) is None]
    missing_cost = [model_code for model_code, _ in public_text_routes if get_text_cost_spec("*", model_code) is None]
    missing_calculator = [
        model_code
        for model_code, route_group in public_text_routes
        if get_text_calculator(route_group=route_group, model_code=model_code) is None
    ]

    assert missing_sale == []
    assert missing_cost == []
    assert missing_calculator == []
