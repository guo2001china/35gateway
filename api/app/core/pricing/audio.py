from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.pricing.common import CNY, power_unit_price
from app.core.pricing.runtime import sale_price_for_model

MINIMAX_SPEECH_28_HD_UNIT_PRICE = Decimal("3.5") / Decimal("10000")
MINIMAX_SPEECH_28_TURBO_UNIT_PRICE = Decimal("2") / Decimal("10000")
QWEN_TTS_VC_UNIT_PRICE = Decimal("0.8") / Decimal("10000")
QWEN_VOICE_CLONE_UNIT_PRICE = Decimal("0.01")


def _is_double_billable_character(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
        or 0x2F800 <= code <= 0x2FA1F
    )


def _count_billable_characters(text: str) -> int:
    return sum(2 if _is_double_billable_character(char) else 1 for char in text)


def quote_qwen_tts_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    input_payload = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    text = str(payload.get("text") or input_payload.get("text") or "")
    billable_characters = _count_billable_characters(text)
    cost_unit_price = QWEN_TTS_VC_UNIT_PRICE
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
    )
    sale_amount = sale_unit_price * Decimal(billable_characters)
    cost_amount = cost_unit_price * Decimal(billable_characters)
    per_power = power_unit_price(sale_unit_price)
    power_amount = per_power * Decimal(billable_characters)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "billable_characters": billable_characters,
            "text_length": len(text),
            "voice": payload.get("voice") or input_payload.get("voice"),
            "language_type": payload.get("language_type") or input_payload.get("language_type"),
        },
        "user_price": {"currency": CNY, "unit_price": str(sale_unit_price)},
        "provider_cost": {"currency": CNY, "unit_price": str(cost_unit_price)},
        "sale_amount": str(sale_amount),
        "sale_currency": CNY,
        "cost_amount": str(cost_amount),
        "cost_currency": CNY,
        "margin_amount": str(sale_amount - cost_amount),
        "power_unit_price": str(per_power),
        "power_amount": str(power_amount),
        "quoted_amount": str(sale_amount),
        "quoted_currency": CNY,
    }
    return sale_amount, CNY, snapshot


def quote_qwen_voice_clone_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    input_payload = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    cost_unit_price = QWEN_VOICE_CLONE_UNIT_PRICE
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
    )
    sale_amount = sale_unit_price
    cost_amount = cost_unit_price
    per_power = power_unit_price(sale_unit_price)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "target_model": payload.get("target_model") or input_payload.get("target_model"),
            "preferred_name": payload.get("preferred_name") or input_payload.get("preferred_name"),
            "has_text": bool(payload.get("text") or input_payload.get("text")),
            "language": payload.get("language") or input_payload.get("language"),
        },
        "user_price": {"currency": CNY, "unit_price": str(sale_unit_price)},
        "provider_cost": {"currency": CNY, "unit_price": str(cost_unit_price)},
        "sale_amount": str(sale_amount),
        "sale_currency": CNY,
        "cost_amount": str(cost_amount),
        "cost_currency": CNY,
        "margin_amount": str(sale_amount - cost_amount),
        "power_unit_price": str(per_power),
        "power_amount": str(per_power),
        "quoted_amount": str(sale_amount),
        "quoted_currency": CNY,
    }
    return sale_amount, CNY, snapshot


def quote_minimax_t2a_async_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    text = str(payload.get("text") or "")
    billed_characters = len(text)
    cost_unit_price = (
        MINIMAX_SPEECH_28_TURBO_UNIT_PRICE
        if model_code == "speech-2.8-turbo"
        else MINIMAX_SPEECH_28_HD_UNIT_PRICE
    )
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
    )
    sale_amount = sale_unit_price * Decimal(billed_characters)
    cost_amount = cost_unit_price * Decimal(billed_characters)
    per_power = power_unit_price(sale_unit_price)
    power_amount = per_power * Decimal(billed_characters)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "billed_characters": billed_characters,
            "text_length": len(text),
            "voice_id": (payload.get("voice_setting") or {}).get("voice_id"),
            "language_boost": payload.get("language_boost"),
            "output_format": (payload.get("audio_setting") or {}).get("format"),
        },
        "user_price": {"currency": CNY, "unit_price": str(sale_unit_price)},
        "provider_cost": {"currency": CNY, "unit_price": str(cost_unit_price)},
        "sale_amount": str(sale_amount),
        "sale_currency": CNY,
        "cost_amount": str(cost_amount),
        "cost_currency": CNY,
        "margin_amount": str(sale_amount - cost_amount),
        "power_unit_price": str(per_power),
        "power_amount": str(power_amount),
        "quoted_amount": str(sale_amount),
        "quoted_currency": CNY,
    }
    return sale_amount, CNY, snapshot
