from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.provider_support import detect_banana_input_mode
from app.core.pricing.common import (
    CNY,
    LAST_VERIFIED_AT,
    ZERO,
    decimal_value,
    extract_image_count,
    extract_image_resolution_key,
    extract_input_image_count,
    margin_summary,
    power_unit_price,
    sale_price_for_target_margin,
    usd_to_cny,
)
from app.core.pricing.runtime import sale_price_for_model


def banana_unit_price(provider_code: str, model_code: str, payload: dict[str, Any]) -> Decimal:
    resolution_key = extract_image_resolution_key(payload)
    if provider_code == "ksyun_openai":
        # Ksyun Gemini image aliases currently expose token pricing. Until we
        # switch this lane to usage-based settlement, keep a conservative
        # fixed-per-image proxy cost so public quotes stay non-zero and stable.
        if model_code == "nano-banana":
            return decimal_value("0.45")
        if model_code == "nano-banana-2":
            if resolution_key == "4K":
                return decimal_value("1.30")
            if resolution_key == "2K":
                return decimal_value("0.95")
            return decimal_value("0.70")
        if model_code == "nano-banana-pro":
            if resolution_key == "4K":
                return decimal_value("1.90")
            return decimal_value("1.20")

    if provider_code == "grsai_nano_banana":
        if model_code == "nano-banana":
            return decimal_value("0.044")
        if model_code == "nano-banana-pro":
            return decimal_value("0.18")
        if model_code == "nano-banana-2":
            return decimal_value("0.12")

    if provider_code == "fal_nano_banana":
        if model_code == "nano-banana":
            return usd_to_cny("0.039")
        if model_code == "nano-banana-pro":
            return usd_to_cny("0.30") if resolution_key == "4K" else usd_to_cny("0.15")
        if model_code == "nano-banana-2":
            if resolution_key == "512":
                return usd_to_cny("0.06")
            if resolution_key == "2K":
                return usd_to_cny("0.12")
            if resolution_key == "4K":
                return usd_to_cny("0.16")
            return usd_to_cny("0.08")

    if model_code == "nano-banana":
        return usd_to_cny("0.039")
    if model_code == "nano-banana-pro":
        return usd_to_cny("0.24") if resolution_key == "4K" else usd_to_cny("0.134")
    if model_code == "nano-banana-2":
        if resolution_key == "512":
            return usd_to_cny("0.045")
        if resolution_key == "2K":
            return usd_to_cny("0.101")
        if resolution_key == "4K":
            return usd_to_cny("0.151")
        return usd_to_cny("0.067")
    return ZERO


def seedream_unit_price(model_code: str) -> Decimal:
    if model_code == "doubao-seedream-4-5-251128":
        return decimal_value("0.25")
    if model_code == "doubao-seedream-5-0-lite-260128":
        return decimal_value("0.008")
    return ZERO


def quote_banana_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    image_count = extract_image_count(payload)
    input_image_count = extract_input_image_count(payload)
    cost_unit_price = banana_unit_price(provider_code, model_code, payload)
    if provider_code == "google_official" and model_code == "nano-banana-pro":
        cost_unit_price += usd_to_cny("0.0011") * Decimal(input_image_count)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(image_count)
    cost_amount = cost_unit_price * Decimal(image_count)
    power_amount = per_power * Decimal(image_count)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "image_count": image_count,
            "input_image_count": input_image_count,
            "aspect_ratio": payload.get("aspect_ratio"),
            "resolution": extract_image_resolution_key(payload),
            "input_mode": detect_banana_input_mode(payload),
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


def quote_seedream_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    image_count = 1
    cost_unit_price = seedream_unit_price(execution_model_code)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(image_count)
    cost_amount = cost_unit_price * Decimal(image_count)
    power_amount = per_power * Decimal(image_count)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "image_count": image_count,
            "size": payload.get("size"),
            "response_format": payload.get("response_format") or "url",
            "has_image": bool(payload.get("image")),
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


def list_image_pricing_items() -> list[dict[str, Any]]:
    return [
        {
            "route_group": "banana",
            "endpoint": "POST /v1/nano-banana",
            "model_code": "nano-banana",
            "billing_unit": "image",
            "currency": CNY,
            "official_price": {
                "output_per_image": str(usd_to_cny("0.039")),
            },
            "sale_price_fields": {
                "output_per_image": str(sale_price_for_target_margin(usd_to_cny("0.039"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "google_official_output_per_image": str(usd_to_cny("0.039")),
                "fal_output_per_image": str(usd_to_cny("0.039")),
                "grsai_public_price_range": "0.022~0.044",
                "grsai_quote_engine_upper_bound": "0.044",
                "ksyun_output_per_image": "0.45",
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(sale_price_for_target_margin(usd_to_cny("0.039"), precision=Decimal("0.0001"))),
                cost_unit_price=str(usd_to_cny("0.039")),
                billing_unit="image",
            ),
            "platform_billing_status": "quoted",
            "notes": "Nano Banana. Supports text-to-image and image-guided editing through Google, Fal, GRSAI and Ksyun. 金山当前按保守固定单图成本代理计价，后续再切到 usage 口径。",
            "source_url": "https://ai.google.dev/gemini-api/docs/image-generation",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "banana",
            "endpoint": "POST /v1/nano-banana-pro",
            "model_code": "nano-banana-pro",
            "billing_unit": "image",
            "currency": CNY,
            "official_price": {
                "output_per_image_1k_2k": str(usd_to_cny("0.134")),
                "output_per_image_4k": str(usd_to_cny("0.24")),
                "input_image_per_image": str(usd_to_cny("0.0011")),
            },
            "sale_price_fields": {
                "output_per_image_1k_2k": str(sale_price_for_target_margin(usd_to_cny("0.134"), precision=Decimal("0.0001"))),
                "output_per_image_4k": str(sale_price_for_target_margin(usd_to_cny("0.24"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "google_official_output_per_image_1k_2k": str(usd_to_cny("0.134")),
                "google_official_output_per_image_4k": str(usd_to_cny("0.24")),
                "fal_output_per_image_1k_2k": str(usd_to_cny("0.15")),
                "fal_output_per_image_4k": str(usd_to_cny("0.30")),
                "grsai_public_price_range": "0.09~0.18",
                "grsai_quote_engine_upper_bound": "0.18",
                "ksyun_output_per_image_1k_2k": "1.20",
                "ksyun_output_per_image_4k": "1.90",
            },
            "margin_snapshot": {
                "billing_unit": "image",
                "status": "provider_variable",
                "notes": "Nano Banana Pro image pricing varies by provider. 金山当前按保守固定单图成本代理计价，后续再切到 usage 口径。",
            },
            "platform_billing_status": "quoted",
            "notes": "Nano Banana Pro. Supports text-to-image and image-guided editing through Google, Fal, GRSAI and Ksyun.",
            "source_url": "https://ai.google.dev/gemini-api/docs/image-generation",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "banana",
            "endpoint": "POST /v1/nano-banana-2",
            "model_code": "nano-banana-2",
            "billing_unit": "image",
            "currency": CNY,
            "official_price": {
                "google_output_per_image_512": str(usd_to_cny("0.045")),
                "google_output_per_image_1k": str(usd_to_cny("0.067")),
                "google_output_per_image_2k": str(usd_to_cny("0.101")),
                "google_output_per_image_4k": str(usd_to_cny("0.151")),
            },
            "sale_price_fields": {
                "output_per_image_1k": str(sale_price_for_target_margin(usd_to_cny("0.067"), precision=Decimal("0.0001"))),
                "output_per_image_2k": str(sale_price_for_target_margin(usd_to_cny("0.101"), precision=Decimal("0.0001"))),
                "output_per_image_4k": str(sale_price_for_target_margin(usd_to_cny("0.151"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "google_output_per_image_512": str(usd_to_cny("0.045")),
                "google_output_per_image_1k": str(usd_to_cny("0.067")),
                "google_output_per_image_2k": str(usd_to_cny("0.101")),
                "google_output_per_image_4k": str(usd_to_cny("0.151")),
                "fal_output_per_image_512": str(usd_to_cny("0.06")),
                "fal_output_per_image_1k": str(usd_to_cny("0.08")),
                "fal_output_per_image_2k": str(usd_to_cny("0.12")),
                "fal_output_per_image_4k": str(usd_to_cny("0.16")),
                "grsai_public_price_range": "0.06~0.12",
                "grsai_quote_engine_upper_bound": "0.12",
                "ksyun_output_per_image_1k": "0.70",
                "ksyun_output_per_image_2k": "0.95",
                "ksyun_output_per_image_4k": "1.30",
            },
            "margin_snapshot": {
                "billing_unit": "image",
                "status": "provider_variable",
                "notes": "Nano Banana 2 image pricing varies by provider. 金山当前按保守固定单图成本代理计价，后续再切到 usage 口径。",
            },
            "platform_billing_status": "quoted",
            "notes": "Nano Banana 2. Supports text-to-image and image-guided editing through Google, Fal, GRSAI and Ksyun.",
            "source_url": "https://ai.google.dev/gemini-api/docs/image-generation",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "seedream",
            "endpoint": "POST /v1/doubao-seedream-4.5",
            "model_code": "doubao-seedream-4.5",
            "billing_unit": "image",
            "currency": CNY,
            "official_price": {
                "per_image": "0.25",
            },
            "sale_price_fields": {
                "per_image": str(sale_price_for_target_margin(decimal_value("0.25"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "per_image": "0.25",
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(sale_price_for_target_margin(decimal_value("0.25"), precision=Decimal("0.0001"))),
                cost_unit_price="0.25",
                billing_unit="image",
            ),
            "platform_billing_status": "quoted",
            "notes": "火山引擎官方计费为 ￥0.25 / 图；Doubao Seedream 4.5 支持 2K / 4K 与自定义像素。",
            "source_url": "https://www.volcengine.com/docs/6492/1544808",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "seedream",
            "endpoint": "POST /v1/doubao-seedream-5.0-lite",
            "model_code": "doubao-seedream-5.0-lite",
            "billing_unit": "image",
            "currency": CNY,
            "official_price": {
                "per_image": "0.008",
            },
            "sale_price_fields": {
                "per_image": str(sale_price_for_target_margin(decimal_value("0.008"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "per_image": "0.008",
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(sale_price_for_target_margin(decimal_value("0.008"), precision=Decimal("0.0001"))),
                cost_unit_price="0.008",
                billing_unit="image",
            ),
            "platform_billing_status": "quoted",
            "notes": "火山引擎官方价格为 ￥0.008 / 图；平台统一以人民币售卖并默认返回 url 结果。",
            "source_url": "https://www.volcengine.com/docs/82379/1520755",
            "last_verified_at": LAST_VERIFIED_AT,
        },
    ]
