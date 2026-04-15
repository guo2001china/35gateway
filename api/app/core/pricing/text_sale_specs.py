from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.pricing.common import decimal_value, sale_price_for_target_margin
from app.core.pricing.text_cost_specs import get_text_cost_spec

TEXT_SALE_SPECS: dict[str, dict[str, Any]] = {
    "gpt-5": {
        "rule_code": "text.gpt_5.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "1.3889",
            "cached_input_per_1m_tokens": "0.1389",
            "output_per_1m_tokens": "11.1111",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://openai.com/api/pricing/",
            "notes": "基于 OpenAI 官方 GPT-5 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "gpt-5.2": {
        "rule_code": "text.gpt_5_2.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "1.9444",
            "cached_input_per_1m_tokens": "0.1944",
            "output_per_1m_tokens": "15.5556",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://openai.com/api/pricing/",
            "notes": "基于 OpenAI 官方 GPT-5.2 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "gpt-5.4": {
        "rule_code": "text.gpt_5_4.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "2.7778",
            "cached_input_per_1m_tokens": "0.2778",
            "output_per_1m_tokens": "16.6667",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://openai.com/api/pricing/",
            "notes": "基于 OpenAI 官方 GPT-5.4 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "gpt-5.4-mini": {
        "rule_code": "text.gpt_5_4_mini.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.8333",
            "cached_input_per_1m_tokens": "0.0833",
            "output_per_1m_tokens": "5.0000",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
            "notes": "基于 OpenAI 官方 GPT-5.4 mini 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "gpt-5.4-nano": {
        "rule_code": "text.gpt_5_4_nano.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.2222",
            "cached_input_per_1m_tokens": "0.0222",
            "output_per_1m_tokens": "1.3889",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://developers.openai.com/api/docs/models/gpt-5.4-nano",
            "notes": "基于 OpenAI 官方 GPT-5.4 nano 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "gpt-5.4-pro": {
        "rule_code": "text.gpt_5_4_pro.flat_tokens",
        "price_fields": {
            "input_per_1m_tokens": "33.3333",
            "output_per_1m_tokens": "200.0000",
        },
        "catalog": {
            "route_group": "responses",
            "endpoint": "POST /v1/responses",
            "source_url": "https://developers.openai.com/api/docs/models/gpt-5.4-pro",
            "notes": "基于 OpenAI 官方 GPT-5.4 Pro 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "毛利率目标 10%，按真实 usage 结算。",
        },
    },
    "DeepSeek-V3.2": {
        "rule_code": "text.deepseek_v3_2.cached_tokens",
        "price_fields": {
            "cache_hit_input_per_1m_tokens": "0.0311",
            "cache_miss_input_per_1m_tokens": "0.3111",
            "output_per_1m_tokens": "0.4667",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://api-docs.deepseek.com/quick_start/pricing",
            "notes": "基于 DeepSeek 官方 V3.2 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "缓存命中/未命中分档；若上游未返回缓存细节则按未命中输入计价。",
        },
    },
    "glm-4.7-flash": {
        "rule_code": "text.cloudflare.flat_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.0667",
            "output_per_1m_tokens": "0.4444",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "notes": "基于 Cloudflare Workers AI 官方价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算。",
        },
    },
    "openrouter-free": {
        "rule_code": "text.openrouter.zero_cost",
        "price_fields": {
            "input_per_1m_tokens": "0",
            "output_per_1m_tokens": "0",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://openrouter.ai/openrouter/free",
            "notes": "OpenRouter 官方 free router 精确资源价格为 0，当前保留为引流资源，不纳入 10% 毛利定价。",
            "margin_notes": "该资源为零成本 promotional 路由，毛利目标不适用。",
        },
    },
    "step-3.5-flash": {
        "rule_code": "text.openrouter.zero_cost",
        "price_fields": {
            "input_per_1m_tokens": "0",
            "output_per_1m_tokens": "0",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://openrouter.ai/stepfun/step-3.5-flash%3Afree",
            "notes": "OpenRouter 官方 :free 资源价格为 0，当前保留为引流资源，不纳入 10% 毛利定价。",
            "margin_notes": "该资源为零成本 promotional 路由，毛利目标不适用。",
        },
    },
    "gemini-2.5-pro": {
        "rule_code": "text.gemini_2_5_pro.input_tiered",
        "price_fields": {
            "input_per_1m_tokens_lte_200k": "1.3889",
            "input_per_1m_tokens_gt_200k": "2.7778",
            "cached_input_per_1m_tokens_lte_200k": "0.1389",
            "cached_input_per_1m_tokens_gt_200k": "0.2778",
            "output_per_1m_tokens_lte_200k": "11.1111",
            "output_per_1m_tokens_gt_200k": "16.6667",
        },
        "catalog": {
            "route_group": "gemini",
            "endpoint": "POST /google/v1beta/models/{model}:generateContent",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 2.5 Pro 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按 200k 输入阈值分档；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "gemini-2.5-flash": {
        "rule_code": "text.gemini_flat.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.3333",
            "cached_input_per_1m_tokens": "0.0333",
            "output_per_1m_tokens": "2.7778",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 2.5 Flash 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "gemini-2.5-flash-lite": {
        "rule_code": "text.gemini_flat.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.1111",
            "cached_input_per_1m_tokens": "0.0111",
            "output_per_1m_tokens": "0.4444",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 2.5 Flash-Lite 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "gemini-3-flash-preview": {
        "rule_code": "text.gemini_flat.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.5556",
            "cached_input_per_1m_tokens": "0.0556",
            "output_per_1m_tokens": "3.3333",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 3 Flash Preview 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "gemini-3.1-pro-preview": {
        "rule_code": "text.gemini_3_1_pro.input_tiered",
        "price_fields": {
            "input_per_1m_tokens_lte_200k": "2.2222",
            "input_per_1m_tokens_gt_200k": "4.4444",
            "cached_input_per_1m_tokens_lte_200k": "0.2222",
            "cached_input_per_1m_tokens_gt_200k": "0.4444",
            "output_per_1m_tokens_lte_200k": "13.3333",
            "output_per_1m_tokens_gt_200k": "20.0000",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 3.1 Pro Preview 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按 200k 输入阈值分档；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "gemini-3.1-flash-lite-preview": {
        "rule_code": "text.gemini_flat.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "0.2778",
            "cached_input_per_1m_tokens": "0.0278",
            "output_per_1m_tokens": "1.6667",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "notes": "基于 Google Gemini 3.1 Flash-Lite Preview 官方 Paid Tier 价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；缓存价仅在上游返回缓存 usage 时生效。",
        },
    },
    "MiniMax-M2.7": {
        "rule_code": "text.minimax_m2_7.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "2.3333",
            "cached_input_per_1m_tokens": "0.4667",
            "output_per_1m_tokens": "9.3333",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://platform.minimaxi.com/docs/guides/pricing-paygo",
            "notes": "基于 MiniMax M2.7 官方按量计费价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；当前缓存写入价格未单独建模。",
        },
    },
    "MiniMax-M2.7-highspeed": {
        "rule_code": "text.minimax_m2_7_highspeed.cached_tokens",
        "price_fields": {
            "input_per_1m_tokens": "4.6667",
            "cached_input_per_1m_tokens": "0.4667",
            "output_per_1m_tokens": "18.6667",
        },
        "catalog": {
            "route_group": "openai",
            "endpoint": "POST /v1/chat/completions",
            "source_url": "https://platform.minimaxi.com/docs/guides/pricing-paygo",
            "notes": "基于 MiniMax M2.7 Highspeed 官方按量计费价格，平台销售价按 10% 毛利反推。",
            "margin_notes": "按真实 input/output token 结算；当前缓存写入价格未单独建模。",
        },
    },
}


def get_text_sale_spec(model_code: str) -> dict[str, Any] | None:
    spec = TEXT_SALE_SPECS.get(model_code)
    if spec is None:
        return None
    resolved = deepcopy(spec)
    cost_spec = get_text_cost_spec("*", model_code) or {}
    cost_fields = dict(cost_spec.get("price_fields") or {})
    if cost_fields:
        resolved["price_fields"] = {
            key: str(
                sale_price_for_target_margin(
                    decimal_value(str(value)),
                    precision=decimal_value("0.000000000001"),
                )
            )
            for key, value in cost_fields.items()
        }
    return resolved
