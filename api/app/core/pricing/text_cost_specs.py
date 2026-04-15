from __future__ import annotations

from typing import Any

from app.core.pricing.common import usd_price_fields_to_cny

DEFAULT_PROVIDER = "*"

TEXT_COST_SPECS: dict[tuple[str, str], dict[str, Any]] = {
    (DEFAULT_PROVIDER, "gpt-5"): {
        "rule_code": "cost.text.gpt_5.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "1.25",
            "cached_input_per_1m_tokens": "0.125",
            "output_per_1m_tokens": "10.00",
        }),
    },
    (DEFAULT_PROVIDER, "gpt-5.2"): {
        "rule_code": "cost.text.gpt_5_2.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "1.75",
            "cached_input_per_1m_tokens": "0.175",
            "output_per_1m_tokens": "14.00",
        }),
    },
    (DEFAULT_PROVIDER, "gpt-5.4"): {
        "rule_code": "cost.text.gpt_5_4.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "2.50",
            "cached_input_per_1m_tokens": "0.25",
            "output_per_1m_tokens": "15.00",
        }),
    },
    (DEFAULT_PROVIDER, "gpt-5.4-mini"): {
        "rule_code": "cost.text.gpt_5_4_mini.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.75",
            "cached_input_per_1m_tokens": "0.075",
            "output_per_1m_tokens": "4.50",
        }),
    },
    (DEFAULT_PROVIDER, "gpt-5.4-nano"): {
        "rule_code": "cost.text.gpt_5_4_nano.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.20",
            "cached_input_per_1m_tokens": "0.02",
            "output_per_1m_tokens": "1.25",
        }),
    },
    (DEFAULT_PROVIDER, "gpt-5.4-pro"): {
        "rule_code": "cost.text.gpt_5_4_pro.flat_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "30.00",
            "output_per_1m_tokens": "180.00",
        }),
    },
    (DEFAULT_PROVIDER, "DeepSeek-V3.2"): {
        "rule_code": "cost.text.deepseek_v3_2.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "cache_hit_input_per_1m_tokens": "0.028",
            "cache_miss_input_per_1m_tokens": "0.28",
            "output_per_1m_tokens": "0.42",
        }),
    },
    (DEFAULT_PROVIDER, "glm-4.7-flash"): {
        "rule_code": "cost.text.cloudflare.flat_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.060",
            "output_per_1m_tokens": "0.400",
        }),
    },
    (DEFAULT_PROVIDER, "openrouter-free"): {
        "rule_code": "cost.text.openrouter.zero_cost",
        "price_fields": {
            "input_per_1m_tokens": "0",
            "output_per_1m_tokens": "0",
        },
    },
    (DEFAULT_PROVIDER, "step-3.5-flash"): {
        "rule_code": "cost.text.openrouter.zero_cost",
        "price_fields": {
            "input_per_1m_tokens": "0",
            "output_per_1m_tokens": "0",
        },
    },
    (DEFAULT_PROVIDER, "gemini-2.5-pro"): {
        "rule_code": "cost.text.gemini_2_5_pro.input_tiered",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens_lte_200k": "1.25",
            "input_per_1m_tokens_gt_200k": "2.50",
            "cached_input_per_1m_tokens_lte_200k": "0.125",
            "cached_input_per_1m_tokens_gt_200k": "0.25",
            "output_per_1m_tokens_lte_200k": "10.00",
            "output_per_1m_tokens_gt_200k": "15.00",
        }),
    },
    (DEFAULT_PROVIDER, "gemini-2.5-flash"): {
        "rule_code": "cost.text.gemini_flat.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.30",
            "cached_input_per_1m_tokens": "0.03",
            "output_per_1m_tokens": "2.50",
        }),
    },
    (DEFAULT_PROVIDER, "gemini-2.5-flash-lite"): {
        "rule_code": "cost.text.gemini_flat.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.10",
            "cached_input_per_1m_tokens": "0.01",
            "output_per_1m_tokens": "0.40",
        }),
    },
    (DEFAULT_PROVIDER, "gemini-3-flash-preview"): {
        "rule_code": "cost.text.gemini_flat.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.50",
            "cached_input_per_1m_tokens": "0.05",
            "output_per_1m_tokens": "3.00",
        }),
    },
    (DEFAULT_PROVIDER, "gemini-3.1-pro-preview"): {
        "rule_code": "cost.text.gemini_3_1_pro.input_tiered",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens_lte_200k": "2.00",
            "input_per_1m_tokens_gt_200k": "4.00",
            "cached_input_per_1m_tokens_lte_200k": "0.20",
            "cached_input_per_1m_tokens_gt_200k": "0.40",
            "output_per_1m_tokens_lte_200k": "12.00",
            "output_per_1m_tokens_gt_200k": "18.00",
        }),
    },
    (DEFAULT_PROVIDER, "gemini-3.1-flash-lite-preview"): {
        "rule_code": "cost.text.gemini_flat.cached_tokens",
        "price_fields": usd_price_fields_to_cny({
            "input_per_1m_tokens": "0.25",
            "cached_input_per_1m_tokens": "0.025",
            "output_per_1m_tokens": "1.50",
        }),
    },
    (DEFAULT_PROVIDER, "MiniMax-M2.7"): {
        "rule_code": "cost.text.minimax_m2_7.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "2.1",
            "cached_input_per_1m_tokens": "0.42",
            "output_per_1m_tokens": "8.4",
        },
    },
    (DEFAULT_PROVIDER, "MiniMax-M2.7-highspeed"): {
        "rule_code": "cost.text.minimax_m2_7_highspeed.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "4.2",
            "cached_input_per_1m_tokens": "0.42",
            "output_per_1m_tokens": "16.8",
        },
    },
}


def get_text_cost_spec(provider_code: str, model_code: str) -> dict[str, Any] | None:
    return TEXT_COST_SPECS.get((provider_code, model_code)) or TEXT_COST_SPECS.get((DEFAULT_PROVIDER, model_code))
