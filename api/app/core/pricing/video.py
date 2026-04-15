from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.kling_video import detect_kling_video_input_mode, resolve_kling_upstream_model, resolve_kling_video_duration, resolve_kling_video_mode
from app.core.provider_support import detect_minimax_video_input_mode, detect_seedance_input_mode, detect_veo_input_mode
from app.core.pricing.common import (
    CNY,
    LAST_VERIFIED_AT,
    ZERO,
    decimal_value,
    extract_seconds,
    extract_veo_resolution_key,
    margin_summary,
    power_unit_price,
    sale_price_for_target_margin,
    usd_to_cny,
)
from app.core.pricing.runtime import sale_price_for_model
from app.core.vidu_video import (
    VIDU_CREDIT_COST_CNY,
    detect_vidu_input_mode,
    quote_vidu_q3_credits,
    resolve_vidu_audio_enabled,
    resolve_vidu_duration,
    resolve_vidu_resolution,
)
from app.core.wan_video import (
    detect_wan_video_input_mode,
    extract_wan_video_resolution_key,
    resolve_wan_video_size,
    resolve_wan_video_upstream_model,
)

def veo_unit_price(provider_code: str, model_code: str, payload: dict[str, Any]) -> Decimal:
    resolution_key = extract_veo_resolution_key(payload)
    generate_audio = bool(payload.get("generate_audio", True))
    if provider_code == "fal_veo3":
        if model_code == "veo-3":
            return usd_to_cny("0.75") if generate_audio else usd_to_cny("0.50")
        if model_code == "veo-3-fast":
            return usd_to_cny("0.40") if generate_audio else usd_to_cny("0.25")
    if provider_code == "fal_veo31":
        if model_code == "veo-3.1-generate-preview":
            if resolution_key == "4k":
                return usd_to_cny("0.60") if generate_audio else usd_to_cny("0.40")
            return usd_to_cny("0.40") if generate_audio else usd_to_cny("0.20")
        if model_code == "veo-3.1-fast-generate-preview":
            if resolution_key == "4k":
                return usd_to_cny("0.35") if generate_audio else usd_to_cny("0.30")
            return usd_to_cny("0.15") if generate_audio else usd_to_cny("0.10")

    if model_code in {"veo-3.0-generate-001", "veo-3.1-generate-preview"}:
        return usd_to_cny("0.60") if resolution_key == "4k" and model_code == "veo-3.1-generate-preview" else usd_to_cny("0.40")
    if model_code in {"veo-3.0-fast-generate-001", "veo-3.1-fast-generate-preview"}:
        return usd_to_cny("0.35") if resolution_key == "4k" and model_code == "veo-3.1-fast-generate-preview" else usd_to_cny("0.15")
    return ZERO


def seedance_unit_price(provider_code: str, model_code: str, payload: dict[str, Any]) -> Decimal:
    input_mode = detect_seedance_input_mode(payload)
    if provider_code not in {"fal_seedance20", "35m"}:
        return ZERO
    if model_code == "seedance-2.0-fast":
        return usd_to_cny("0.2419")
    if model_code == "seedance-2.0":
        if input_mode == "text":
            return usd_to_cny("0.3034")
        return usd_to_cny("0.3024")
    return ZERO


def _normalize_minimax_video_model_code(model_code: str) -> str:
    mapping = {
        "minimax-hailuo-2.3": "MiniMax-Hailuo-2.3",
        "minimax-hailuo-2.3-fast": "MiniMax-Hailuo-2.3-Fast",
        "minimax-hailuo-02": "MiniMax-Hailuo-02",
    }
    return mapping.get(model_code, model_code)


def extract_minimax_video_resolution_key(payload: dict[str, Any], *, default: str = "768P") -> str:
    resolution = str(payload.get("resolution") or default).upper()
    if resolution in {"512P", "768P", "1080P"}:
        return resolution
    return default


def minimax_video_unit_price(model_code: str, payload: dict[str, Any]) -> Decimal:
    normalized_model = _normalize_minimax_video_model_code(model_code)
    input_mode = detect_minimax_video_input_mode(payload)
    seconds = extract_seconds(payload) or 6
    resolution_key = extract_minimax_video_resolution_key(payload)

    if normalized_model == "MiniMax-Hailuo-2.3-Fast":
        if resolution_key == "1080P":
            return decimal_value("2.31")
        if seconds >= 10:
            return decimal_value("2.25")
        return decimal_value("1.35")

    if normalized_model in {"MiniMax-Hailuo-2.3", "MiniMax-Hailuo-02"}:
        if normalized_model == "MiniMax-Hailuo-02" and input_mode in {"image", "first_last_frame"} and resolution_key == "512P":
            if seconds >= 10:
                return decimal_value("1.00")
            return decimal_value("0.60")
        if resolution_key == "1080P":
            return decimal_value("3.50")
        if seconds >= 10:
            return decimal_value("4.00")
        return decimal_value("2.00")

    return ZERO


def wan_video_unit_price(model_code: str, payload: dict[str, Any]) -> Decimal:
    resolved_model = resolve_wan_video_upstream_model(model_code, payload)
    if resolved_model is None:
        return ZERO

    resolution_key = extract_wan_video_resolution_key(payload)
    generate_audio = True if payload.get("generate_audio") is None else bool(payload.get("generate_audio"))

    if resolved_model == "wan2.6-t2v":
        return decimal_value("1.00") if resolution_key == "1080P" else decimal_value("0.60")

    if resolved_model in {"wan2.6-i2v", "wan2.6-r2v"}:
        return decimal_value("1.00") if resolution_key == "1080P" else decimal_value("0.60")

    if resolved_model in {"wan2.6-i2v-flash", "wan2.6-r2v-flash"}:
        if resolution_key == "1080P":
            return decimal_value("0.50" if generate_audio else "0.25")
        return decimal_value("0.30" if generate_audio else "0.15")

    return ZERO


def kling_video_unit_price(model_code: str, payload: dict[str, Any]) -> Decimal:
    resolved_model = resolve_kling_upstream_model(model_code)
    if resolved_model != "kling-video-o1":
        return ZERO

    mode = resolve_kling_video_mode(payload)
    has_video_input = detect_kling_video_input_mode(payload) == "video_reference"

    if mode == "std":
        return decimal_value("0.90" if has_video_input else "0.60")
    return decimal_value("1.20" if has_video_input else "0.80")


def vidu_credit_sale_price(model_code: str) -> Decimal:
    return sale_price_for_model(
        model_code=model_code,
        cost_unit_price=VIDU_CREDIT_COST_CNY,
        precision=Decimal("0.00000001"),
    )


def quote_vidu_video_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    quoted_credits = quote_vidu_q3_credits(model_code=execution_model_code, payload=payload)
    cost_unit_price = VIDU_CREDIT_COST_CNY
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.00000001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * quoted_credits
    cost_amount = cost_unit_price * quoted_credits
    power_amount = per_power * quoted_credits
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "mode": detect_vidu_input_mode(payload),
            "duration": resolve_vidu_duration(payload),
            "resolution": resolve_vidu_resolution(payload),
            "audio": resolve_vidu_audio_enabled(payload),
            "off_peak": bool(payload.get("off_peak")),
            "is_rec": bool(payload.get("is_rec")),
            "credits": str(quoted_credits),
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
        "credits": str(quoted_credits),
    }
    return sale_amount, CNY, snapshot

def quote_veo_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    seconds = extract_seconds(payload) or 8
    cost_unit_price = veo_unit_price(provider_code, execution_model_code, payload)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(seconds)
    cost_amount = cost_unit_price * Decimal(seconds)
    power_amount = per_power * Decimal(seconds)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "seconds": seconds,
            "resolution": payload.get("resolution", "720p"),
            "aspect_ratio": payload.get("aspect_ratio"),
            "input_mode": detect_veo_input_mode(payload),
            "generate_audio": bool(payload.get("generate_audio", True)),
            "has_input_reference": bool(payload.get("input_reference") or payload.get("image") or payload.get("image_url")),
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


def quote_seedance_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    seconds = extract_seconds(payload) or 4
    cost_unit_price = seedance_unit_price(provider_code, execution_model_code, payload)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(seconds)
    cost_amount = cost_unit_price * Decimal(seconds)
    power_amount = per_power * Decimal(seconds)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "seconds": seconds,
            "resolution": payload.get("resolution", "720p"),
            "aspect_ratio": payload.get("aspect_ratio"),
            "input_mode": detect_seedance_input_mode(payload),
            "generate_audio": bool(payload.get("generate_audio", True)),
            "has_input_reference": bool(payload.get("input_reference") or payload.get("image") or payload.get("image_url")),
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


def quote_minimax_video_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    seconds = extract_seconds(payload) or 6
    resolution_key = extract_minimax_video_resolution_key(payload)
    cost_unit_price = minimax_video_unit_price(execution_model_code, payload)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price
    cost_amount = cost_unit_price
    power_amount = per_power
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "seconds": seconds,
            "resolution": resolution_key,
            "aspect_ratio": payload.get("aspect_ratio"),
            "input_mode": detect_minimax_video_input_mode(payload),
            "has_input_reference": bool(payload.get("input_reference") or payload.get("first_frame")),
            "has_last_frame": bool(payload.get("last_frame")),
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


def quote_wan_video_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    seconds = extract_seconds(payload) or 5
    cost_unit_price = wan_video_unit_price(execution_model_code, payload)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(seconds)
    cost_amount = cost_unit_price * Decimal(seconds)
    power_amount = per_power * Decimal(seconds)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "seconds": seconds,
            "size": resolve_wan_video_size(payload),
            "resolution": extract_wan_video_resolution_key(payload),
            "input_mode": detect_wan_video_input_mode(payload),
            "generate_audio": True if payload.get("generate_audio") is None else bool(payload.get("generate_audio")),
            "reference_count": len(payload.get("reference_urls") or []),
            "resolved_model": resolve_wan_video_upstream_model(execution_model_code, payload),
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


def quote_kling_video_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    model_code: str,
    public_model_code: str | None,
    billing_unit: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    seconds = resolve_kling_video_duration(payload)
    cost_unit_price = kling_video_unit_price(execution_model_code, payload)
    sale_unit_price = sale_price_for_model(
        model_code=model_code,
        cost_unit_price=cost_unit_price,
        precision=Decimal("0.0001"),
    )
    per_power = power_unit_price(sale_unit_price)
    sale_amount = sale_unit_price * Decimal(seconds)
    cost_amount = cost_unit_price * Decimal(seconds)
    power_amount = per_power * Decimal(seconds)
    snapshot = {
        "model": model_code,
        "provider_code": provider_code,
        "route_group": route_group,
        "billing_unit": billing_unit,
        "request_factors": {
            "seconds": seconds,
            "mode": resolve_kling_video_mode(payload),
            "input_mode": detect_kling_video_input_mode(payload),
            "has_video_input": detect_kling_video_input_mode(payload) == "video_reference",
            "reference_image_count": len(payload.get("reference_images") or []),
            "resolved_model": resolve_kling_upstream_model(execution_model_code),
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


def list_video_pricing_items() -> list[dict[str, Any]]:
    return [
        {
            "route_group": "kling_video",
            "endpoint": "POST /v1/kling-o1",
            "model_code": "kling-o1",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "std_without_video_input_per_second": "0.60",
                "std_with_video_input_per_second": "0.90",
                "pro_without_video_input_per_second": "0.80",
                "pro_with_video_input_per_second": "1.20",
            },
            "sale_price_fields": {
                "std_without_video_input_per_second": str(sale_price_for_target_margin(decimal_value("0.60"), precision=Decimal("0.0001"))),
                "std_with_video_input_per_second": str(sale_price_for_target_margin(decimal_value("0.90"), precision=Decimal("0.0001"))),
                "pro_without_video_input_per_second": str(sale_price_for_target_margin(decimal_value("0.80"), precision=Decimal("0.0001"))),
                "pro_with_video_input_per_second": str(sale_price_for_target_margin(decimal_value("1.20"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "std_without_video_input_per_second": "0.60",
                "std_with_video_input_per_second": "0.90",
                "pro_without_video_input_per_second": "0.80",
                "pro_with_video_input_per_second": "1.20",
            },
            "margin_snapshot": {
                "billing_unit": "second",
                "status": "tiered",
                "notes": "按 std/pro 与是否包含参考视频分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "Kling O1 当前对外收口文生、单图、多参考图、视频参考和首尾帧视频。",
            "source_url": "https://app.klingai.com/global/dev/document-api/productBilling/prePaidResourcePackage",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "wan_video",
            "endpoint": "POST /v1/wan2.6",
            "model_code": "wan2.6",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "720p_per_second": "0.60",
                "1080p_per_second": "1.00",
            },
            "sale_price_fields": {
                "720p_per_second": str(sale_price_for_target_margin(decimal_value("0.60"), precision=Decimal("0.0001"))),
                "1080p_per_second": str(sale_price_for_target_margin(decimal_value("1.00"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "720p_per_second": "0.60",
                "1080p_per_second": "1.00",
            },
            "margin_snapshot": {
                "billing_unit": "second",
                "status": "tiered",
                "notes": "按分辨率分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "Wan 2.6 当前对外收口文生、图生和参考生视频，并按真实解析后的子模型计价。",
            "source_url": "https://help.aliyun.com/zh/model-studio/model-pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "wan_video",
            "endpoint": "POST /v1/wan2.6-flash",
            "model_code": "wan2.6-flash",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "720p_with_audio_per_second": "0.30",
                "1080p_with_audio_per_second": "0.50",
                "720p_silent_per_second": "0.15",
                "1080p_silent_per_second": "0.25",
            },
            "sale_price_fields": {
                "720p_with_audio_per_second": str(sale_price_for_target_margin(decimal_value("0.30"), precision=Decimal("0.0001"))),
                "1080p_with_audio_per_second": str(sale_price_for_target_margin(decimal_value("0.50"), precision=Decimal("0.0001"))),
                "720p_silent_per_second": str(sale_price_for_target_margin(decimal_value("0.15"), precision=Decimal("0.0001"))),
                "1080p_silent_per_second": str(sale_price_for_target_margin(decimal_value("0.25"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "720p_with_audio_per_second": "0.30",
                "1080p_with_audio_per_second": "0.50",
                "720p_silent_per_second": "0.15",
                "1080p_silent_per_second": "0.25",
            },
            "margin_snapshot": {
                "billing_unit": "second",
                "status": "tiered",
                "notes": "按分辨率与是否带音频分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "Wan 2.6 Flash 当前对外收口图生和参考生视频，并支持静音档位。",
            "source_url": "https://help.aliyun.com/zh/model-studio/model-pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "vidu",
            "endpoint": "POST /v1/viduq3-pro",
            "model_code": "viduq3-pro",
            "billing_unit": "credit",
            "currency": CNY,
            "official_price": {
                "540p_per_second_credits": "10",
                "720p_per_second_credits": "25",
                "1080p_per_second_credits": "30",
                "540p_off_peak_per_second_credits": "5",
                "720p_off_peak_per_second_credits": "13",
                "1080p_off_peak_per_second_credits": "15",
                "is_rec_extra_credits": "10",
                "credit_cost_cny": str(VIDU_CREDIT_COST_CNY),
            },
            "sale_price_fields": {
                "per_credit": str(vidu_credit_sale_price("viduq3-pro")),
            },
            "provider_cost": {
                "per_credit": str(VIDU_CREDIT_COST_CNY),
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(vidu_credit_sale_price("viduq3-pro")),
                cost_unit_price=str(VIDU_CREDIT_COST_CNY),
                billing_unit="credit",
            ),
            "platform_billing_status": "quoted",
            "notes": "Vidu Q3 Pro 按官方积分规则换算为人民币和算力；错峰价仅在 audio=true 时适用，is_rec 每次额外增加 10 积分。",
            "source_url": "https://platform.vidu.cn/docs/pricing",
            "last_verified_at": "2026-04-10",
        },
        {
            "route_group": "vidu",
            "endpoint": "POST /v1/viduq3-turbo",
            "model_code": "viduq3-turbo",
            "billing_unit": "credit",
            "currency": CNY,
            "official_price": {
                "540p_per_second_credits": "8",
                "720p_per_second_credits": "12",
                "1080p_per_second_credits": "14",
                "540p_off_peak_per_second_credits": "4",
                "720p_off_peak_per_second_credits": "6",
                "1080p_off_peak_per_second_credits": "7",
                "is_rec_extra_credits": "10",
                "credit_cost_cny": str(VIDU_CREDIT_COST_CNY),
            },
            "sale_price_fields": {
                "per_credit": str(vidu_credit_sale_price("viduq3-turbo")),
            },
            "provider_cost": {
                "per_credit": str(VIDU_CREDIT_COST_CNY),
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(vidu_credit_sale_price("viduq3-turbo")),
                cost_unit_price=str(VIDU_CREDIT_COST_CNY),
                billing_unit="credit",
            ),
            "platform_billing_status": "quoted",
            "notes": "Vidu Q3 Turbo 按官方积分规则换算为人民币和算力；错峰价仅在 audio=true 时适用，is_rec 每次额外增加 10 积分。",
            "source_url": "https://platform.vidu.cn/docs/pricing",
            "last_verified_at": "2026-04-10",
        },
        {
            "route_group": "minimax_video",
            "endpoint": "POST /v1/minimax-hailuo-2.3",
            "model_code": "minimax-hailuo-2.3",
            "billing_unit": "video",
            "currency": CNY,
            "official_price": {
                "768p_6s": "2.00",
                "768p_10s": "4.00",
                "1080p_6s": "3.50",
            },
            "sale_price_fields": {
                "768p_6s": str(sale_price_for_target_margin(decimal_value("2.00"), precision=Decimal("0.0001"))),
                "768p_10s": str(sale_price_for_target_margin(decimal_value("4.00"), precision=Decimal("0.0001"))),
                "1080p_6s": str(sale_price_for_target_margin(decimal_value("3.50"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "768p_6s": "2.00",
                "768p_10s": "4.00",
                "1080p_6s": "3.50",
            },
            "margin_snapshot": {
                "billing_unit": "video",
                "status": "tiered",
                "notes": "按分辨率与时长分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "MiniMax Hailuo 2.3 当前支持文生和图生视频。",
            "source_url": "https://platform.minimaxi.com/docs/guides/pricing-paygo",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "minimax_video",
            "endpoint": "POST /v1/minimax-hailuo-2.3-fast",
            "model_code": "minimax-hailuo-2.3-fast",
            "billing_unit": "video",
            "currency": CNY,
            "official_price": {
                "768p_6s": "1.35",
                "768p_10s": "2.25",
                "1080p_6s": "2.31",
            },
            "sale_price_fields": {
                "768p_6s": str(sale_price_for_target_margin(decimal_value("1.35"), precision=Decimal("0.0001"))),
                "768p_10s": str(sale_price_for_target_margin(decimal_value("2.25"), precision=Decimal("0.0001"))),
                "1080p_6s": str(sale_price_for_target_margin(decimal_value("2.31"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "768p_6s": "1.35",
                "768p_10s": "2.25",
                "1080p_6s": "2.31",
            },
            "margin_snapshot": {
                "billing_unit": "video",
                "status": "tiered",
                "notes": "按分辨率与时长分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "MiniMax Hailuo 2.3 Fast 当前主打图生视频。",
            "source_url": "https://platform.minimaxi.com/docs/guides/pricing-paygo",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "minimax_video",
            "endpoint": "POST /v1/minimax-hailuo-02",
            "model_code": "minimax-hailuo-02",
            "billing_unit": "video",
            "currency": CNY,
            "official_price": {
                "text_or_image_768p_6s": "2.00",
                "text_or_image_768p_10s": "4.00",
                "text_or_image_1080p_6s": "3.50",
                "image_512p_6s": "0.60",
                "image_512p_10s": "1.00",
            },
            "sale_price_fields": {
                "text_or_image_768p_6s": str(sale_price_for_target_margin(decimal_value("2.00"), precision=Decimal("0.0001"))),
                "text_or_image_768p_10s": str(sale_price_for_target_margin(decimal_value("4.00"), precision=Decimal("0.0001"))),
                "text_or_image_1080p_6s": str(sale_price_for_target_margin(decimal_value("3.50"), precision=Decimal("0.0001"))),
                "image_512p_6s": str(sale_price_for_target_margin(decimal_value("0.60"), precision=Decimal("0.0001"))),
                "image_512p_10s": str(sale_price_for_target_margin(decimal_value("1.00"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "text_or_image_768p_6s": "2.00",
                "text_or_image_768p_10s": "4.00",
                "text_or_image_1080p_6s": "3.50",
                "image_512p_6s": "0.60",
                "image_512p_10s": "1.00",
            },
            "margin_snapshot": {
                "billing_unit": "video",
                "status": "tiered",
                "notes": "按输入模式、分辨率与时长分档；平台统一按官方人民币价加 10% 毛利。",
            },
            "platform_billing_status": "quoted",
            "notes": "MiniMax Hailuo 02 当前支持文生、图生和首尾帧视频。",
            "source_url": "https://platform.minimaxi.com/docs/guides/pricing-paygo",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "veo3",
            "endpoint": "POST /v1/veo-3",
            "model_code": "veo-3",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "per_second": str(usd_to_cny("0.40")),
            },
            "sale_price_fields": {
                "per_second": str(sale_price_for_target_margin(usd_to_cny("0.40"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "per_second": str(usd_to_cny("0.40")),
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(sale_price_for_target_margin(usd_to_cny("0.40"), precision=Decimal("0.0001"))),
                cost_unit_price=str(usd_to_cny("0.40")),
                billing_unit="second",
            ),
            "platform_billing_status": "quoted",
            "notes": "Veo 3 标准版稳定模型；美元供应商按固定 1:7 折算人民币。",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "veo3",
            "endpoint": "POST /v1/veo-3-fast",
            "model_code": "veo-3-fast",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "per_second": str(usd_to_cny("0.15")),
            },
            "sale_price_fields": {
                "per_second": str(sale_price_for_target_margin(usd_to_cny("0.15"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "per_second": str(usd_to_cny("0.15")),
            },
            "margin_snapshot": margin_summary(
                sale_unit_price=str(sale_price_for_target_margin(usd_to_cny("0.15"), precision=Decimal("0.0001"))),
                cost_unit_price=str(usd_to_cny("0.15")),
                billing_unit="second",
            ),
            "platform_billing_status": "quoted",
            "notes": "Veo 3 Fast 稳定模型；美元供应商按固定 1:7 折算人民币。",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "veo31",
            "endpoint": "POST /v1/veo-3.1",
            "model_code": "veo-3.1",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "720p_or_1080p_per_second": str(usd_to_cny("0.40")),
                "4k_per_second": str(usd_to_cny("0.60")),
            },
            "sale_price_fields": {
                "720p_or_1080p_per_second": str(sale_price_for_target_margin(usd_to_cny("0.40"), precision=Decimal("0.0001"))),
                "4k_per_second": str(sale_price_for_target_margin(usd_to_cny("0.60"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "720p_or_1080p_per_second": str(usd_to_cny("0.40")),
                "4k_per_second": str(usd_to_cny("0.60")),
            },
            "margin_snapshot": {
                "billing_unit": "second",
                "status": "tiered",
                "notes": "按分辨率分档；美元供应商按固定 1:7 折算人民币。",
            },
            "platform_billing_status": "quoted",
            "notes": "Veo 3.1 标准版预览模型。",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
        {
            "route_group": "veo31",
            "endpoint": "POST /v1/veo-3.1-fast",
            "model_code": "veo-3.1-fast",
            "billing_unit": "second",
            "currency": CNY,
            "official_price": {
                "720p_or_1080p_per_second": str(usd_to_cny("0.15")),
                "4k_per_second": str(usd_to_cny("0.35")),
            },
            "sale_price_fields": {
                "720p_or_1080p_per_second": str(sale_price_for_target_margin(usd_to_cny("0.15"), precision=Decimal("0.0001"))),
                "4k_per_second": str(sale_price_for_target_margin(usd_to_cny("0.35"), precision=Decimal("0.0001"))),
            },
            "provider_cost": {
                "720p_or_1080p_per_second": str(usd_to_cny("0.15")),
                "4k_per_second": str(usd_to_cny("0.35")),
            },
            "margin_snapshot": {
                "billing_unit": "second",
                "status": "tiered",
                "notes": "按分辨率分档；美元供应商按固定 1:7 折算人民币。",
            },
            "platform_billing_status": "quoted",
            "notes": "Veo 3.1 Fast 预览模型。",
            "source_url": "https://ai.google.dev/gemini-api/docs/pricing",
            "last_verified_at": LAST_VERIFIED_AT,
        },
    ]
