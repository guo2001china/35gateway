from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.pricing.common import apply_multiplier_to_price_fields
from app.domains.platform.services.model_metrics import ModelMetricsService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.provider_metrics import MIN_SAMPLE_COUNT

_CATEGORY_ORDER = {"text": 0, "image": 1, "video": 2, "audio": 3}
_RELEASE_ORDER = {
    "text": {
        "gpt-5.4": 0,
        "gpt-5.4-pro": 1,
        "gpt-5.4-mini": 2,
        "gpt-5.4-nano": 3,
        "gemini-3.1-pro-preview": 4,
        "gemini-3.1-flash-lite-preview": 5,
        "gemini-3-flash-preview": 6,
        "DeepSeek-V3.2": 7,
        "MiniMax-M2.7": 8,
        "MiniMax-M2.7-highspeed": 9,
        "glm-4.7-flash": 10,
        "gemini-2.5-pro": 11,
        "gemini-2.5-flash": 12,
        "gemini-2.5-flash-lite": 13,
        "step-3.5-flash": 14,
        "openrouter-free": 15,
    },
    "image": {
        "doubao-seedream-5.0-lite": 0,
        "nano-banana-2": 1,
        "nano-banana-pro": 2,
        "doubao-seedream-4.5": 3,
        "nano-banana": 4,
    },
    "video": {
        "seedance-2.0-fast": 0,
        "seedance-2.0": 1,
        "veo-3.1-fast": 2,
        "veo-3.1": 3,
        "veo-3-fast": 4,
        "veo-3": 5,
        "minimax-hailuo-02": 6,
        "kling-o1": 7,
        "wan2.6-flash": 8,
        "wan2.6": 9,
        "viduq3-turbo": 10,
        "viduq3-pro": 11,
    },
    "audio": {
        "speech-2.8-hd": 0,
        "speech-2.8-turbo": 1,
        "qwen3-tts-instruct-flash": 2,
        "qwen3-tts-flash": 3,
        "qwen3-tts-vc-2026-01-22": 4,
        "qwen-voice-enrollment": 5,
    },
}
_PRICE_KEY_LABELS = {
    "input_per_1m_tokens": "输入",
    "cache_miss_input_per_1m_tokens": "缓存未命中输入",
    "cached_input_per_1m_tokens": "缓存命中输入",
    "cache_hit_input_per_1m_tokens": "缓存命中输入",
    "output_per_1m_tokens": "输出",
    "text_to_video_per_second": "文生",
    "image_to_video_per_second": "图生",
    "reference_to_video_per_second": "参考图/视频",
    "per_image": "参考价",
    "output_per_image": "参考价",
    "per_second": "参考价",
    "720p_or_1080p_per_second": "720p / 1080p",
    "720p_per_second": "720p",
    "1080p_per_second": "1080p",
    "4k_per_second": "4K",
    "std_without_video_input_per_second": "标准无视频参考",
    "std_with_video_input_per_second": "标准视频参考",
    "pro_without_video_input_per_second": "专业无视频参考",
    "pro_with_video_input_per_second": "专业视频参考",
    "540p_per_second_credits": "540p",
    "720p_per_second_credits": "720p",
    "1080p_per_second_credits": "1080p",
    "540p_off_peak_per_second_credits": "540p 闲时",
    "720p_off_peak_per_second_credits": "720p 闲时",
    "1080p_off_peak_per_second_credits": "1080p 闲时",
    "720p_with_audio_per_second": "720p 含音频",
    "1080p_with_audio_per_second": "1080p 含音频",
    "720p_silent_per_second": "720p 静音",
    "1080p_silent_per_second": "1080p 静音",
    "per_billable_character": "参考价",
    "per_character": "参考价",
    "per_voice": "参考价",
}
_PRICE_KEY_ORDER = {
    "input_per_1m_tokens": 0,
    "cache_miss_input_per_1m_tokens": 1,
    "cached_input_per_1m_tokens": 2,
    "cache_hit_input_per_1m_tokens": 3,
    "output_per_1m_tokens": 4,
    "output_per_image": 10,
    "per_image": 11,
    "720p_or_1080p_per_second": 12,
    "720p_per_second": 13,
    "1080p_per_second": 14,
    "4k_per_second": 15,
    "text_to_video_per_second": 16,
    "image_to_video_per_second": 17,
    "reference_to_video_per_second": 18,
    "std_without_video_input_per_second": 19,
    "std_with_video_input_per_second": 20,
    "pro_without_video_input_per_second": 21,
    "pro_with_video_input_per_second": 22,
    "720p_with_audio_per_second": 23,
    "1080p_with_audio_per_second": 24,
    "720p_silent_per_second": 25,
    "1080p_silent_per_second": 26,
    "540p_per_second_credits": 27,
    "720p_per_second_credits": 28,
    "1080p_per_second_credits": 29,
    "540p_off_peak_per_second_credits": 30,
    "720p_off_peak_per_second_credits": 31,
    "1080p_off_peak_per_second_credits": 32,
    "per_second": 33,
    "per_billable_character": 20,
    "per_character": 21,
    "per_voice": 22,
}
_TEXT_TIER_SUFFIXES = ("_lte_200k", "_gt_200k")


def _currency_prefix(currency: str | None) -> str:
    normalized = str(currency or "CNY").upper()
    if normalized == "CNY":
        return "¥"
    return f"{normalized} "


def _format_decimal(value: Any) -> str:
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    absolute = abs(numeric)
    if absolute >= Decimal("100"):
        quantized = numeric.quantize(Decimal("0.01"))
    elif absolute >= Decimal("0.01"):
        quantized = numeric.quantize(Decimal("0.0001"))
    else:
        quantized = numeric.quantize(Decimal("0.00000001"))
    text = format(quantized.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _unit_suffix(price_key: str) -> str:
    if price_key in {
        "input_per_1m_tokens",
        "cache_miss_input_per_1m_tokens",
        "cached_input_per_1m_tokens",
        "cache_hit_input_per_1m_tokens",
        "output_per_1m_tokens",
    }:
        return "/ 1M tokens"
    if price_key in {"output_per_image", "per_image"}:
        return "/ 图"
    if price_key in {"per_second", "720p_or_1080p_per_second", "4k_per_second", "720p_per_second", "1080p_per_second"}:
        return "/ 秒"
    if price_key in {"per_billable_character", "per_character"}:
        return "/ 字"
    if price_key == "per_voice":
        return "/ 个音色"
    return ""


def _safe_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _format_price_value(*, prefix: str, value: Decimal, unit_suffix: str) -> str:
    return f"{prefix}{_format_decimal(value)} {unit_suffix}".replace("  ", " ").strip()


def _normalize_text_price_key(key: str) -> str:
    for suffix in _TEXT_TIER_SUFFIXES:
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def _text_price_lines(*, currency: str | None, sale_price: dict[str, Any]) -> list[dict[str, str]]:
    prefix = _currency_prefix(currency)
    grouped_values: dict[str, list[Decimal]] = {}
    for key, raw_value in sale_price.items():
        numeric = _safe_decimal(raw_value)
        if numeric is None:
            continue
        normalized_key = _normalize_text_price_key(key)
        grouped_values.setdefault(normalized_key, []).append(numeric)

    lines: list[dict[str, str]] = []
    for key in sorted(grouped_values.keys(), key=lambda item: (_PRICE_KEY_ORDER.get(item, 99), item)):
        values = sorted(grouped_values[key])
        label = _PRICE_KEY_LABELS.get(key, key.replace("_", " "))
        unit_suffix = _unit_suffix(key)
        if not values:
            continue
        if values[0] == values[-1]:
            value = _format_price_value(prefix=prefix, value=values[0], unit_suffix=unit_suffix)
        else:
            minimum = _format_price_value(prefix=prefix, value=values[0], unit_suffix=unit_suffix)
            maximum = _format_price_value(prefix=prefix, value=values[-1], unit_suffix=unit_suffix)
            value = f"{minimum} - {maximum.replace(prefix, '', 1)}"
        lines.append({"label": label, "value": value})

    return lines


def _catalog_unit_suffix_for_billing_unit(billing_unit: str | None) -> str:
    normalized = str(billing_unit or "").lower()
    mapping = {
        "image": "/ 图",
        "second": "/ 秒",
        "video": "/ 次",
        "character": "/ 字",
        "voice": "/ 个音色",
        "credit": "/ 点数",
    }
    return mapping.get(normalized, "")


def _catalog_price_lines(*, currency: str | None, billing_unit: str | None, sale_price: dict[str, Any]) -> list[dict[str, str]]:
    prefix = _currency_prefix(currency)
    numeric_items = [
        (key, numeric)
        for key, raw_value in sale_price.items()
        if (numeric := _safe_decimal(raw_value)) is not None
    ]
    if not numeric_items:
        return []

    ordered_items = sorted(numeric_items, key=lambda item: (_PRICE_KEY_ORDER.get(item[0], 99), item[0]))
    first_key = ordered_items[0][0]
    unit_suffix = _catalog_unit_suffix_for_billing_unit(billing_unit)
    if len(ordered_items) == 1:
        return [
            {
                "label": _PRICE_KEY_LABELS.get(first_key, "参考价"),
                "value": _format_price_value(prefix=prefix, value=ordered_items[0][1], unit_suffix=unit_suffix),
            }
        ]
    if all(key in _PRICE_KEY_LABELS for key, _ in ordered_items):
        return [
            {
                "label": _PRICE_KEY_LABELS[key],
                "value": _format_price_value(prefix=prefix, value=value, unit_suffix=unit_suffix),
            }
            for key, value in ordered_items
        ]
    values = sorted(item[1] for item in ordered_items)
    return [
        {
            "label": "最低",
            "value": _format_price_value(prefix=prefix, value=values[0], unit_suffix=unit_suffix),
        },
        {
            "label": "最高",
            "value": _format_price_value(prefix=prefix, value=values[-1], unit_suffix=unit_suffix),
        },
    ]


def build_public_model_price_lines(
    *,
    category: str,
    currency: str | None,
    billing_unit: str | None,
    sale_price: dict[str, Any],
) -> list[dict[str, str]]:
    if category == "text":
        return _text_price_lines(currency=currency, sale_price=sale_price)
    return _catalog_price_lines(currency=currency, billing_unit=billing_unit, sale_price=sale_price)


class PublicModelPricingService:
    def __init__(self, db: Session):
        self.db = db
        self.model_metrics = ModelMetricsService(db)

    def _serialize_availability(
        self,
        *,
        window: str,
        sample_count: int,
        success_count: int,
    ) -> dict[str, Any] | None:
        if sample_count < MIN_SAMPLE_COUNT or sample_count <= 0:
            return None
        return {
            "window": window,
            "sample_count": sample_count,
            "success_rate": round((success_count / sample_count) * 100, 2),
        }

    def _availability_by_model(self, snapshot, *, window: str = "24h") -> dict[str, dict[str, Any]]:
        route_map: dict[str, str] = {}
        for model in snapshot.list_public_models():
            route = snapshot.get_primary_route(model.public_model_code, public_only=True)
            if route is None:
                continue
            route_map[model.public_model_code] = route.route_group

        availability_by_model: dict[str, dict[str, Any]] = {}
        for public_model_code, metrics in self.model_metrics.metrics_for_route_map(route_map, window).items():
            availability = self._serialize_availability(
                window=str(metrics["window"]),
                sample_count=int(metrics["sample_count"]),
                success_count=int(metrics["success_count"]),
            )
            if availability is not None:
                availability_by_model[public_model_code] = availability
        return availability_by_model

    def list_models(self) -> list[dict[str, Any]]:
        snapshot = get_platform_config_snapshot()
        availability_by_model = self._availability_by_model(snapshot)
        items: list[dict[str, Any]] = []

        for model in snapshot.list_public_models():
            route = snapshot.get_primary_route(model.public_model_code, public_only=True)
            if route is None:
                continue
            pricing_snapshot = snapshot.get_pricing_for_model(model.public_model_code)
            sale_price = dict(pricing_snapshot.sale_price_fields or {}) if pricing_snapshot else {}
            if pricing_snapshot and model.category != "text":
                derived_sale_price = apply_multiplier_to_price_fields(
                    dict(pricing_snapshot.provider_cost or {}),
                    multiplier=pricing_snapshot.multiplier,
                    precision=Decimal("0.0001"),
                )
                if derived_sale_price:
                    sale_price = derived_sale_price
            lines = build_public_model_price_lines(
                category=model.category,
                currency=pricing_snapshot.currency if pricing_snapshot else None,
                billing_unit=pricing_snapshot.billing_unit if pricing_snapshot else None,
                sale_price=sale_price,
            )
            items.append(
                {
                    "model_code": model.public_model_code,
                    "display_name": model.display_name,
                    "category": model.category,
                    "summary": model.summary,
                    "supported_input_modes": list(route.supported_input_modes),
                    "pricing": {
                        "currency": pricing_snapshot.currency if pricing_snapshot else None,
                        "billing_unit": pricing_snapshot.billing_unit if pricing_snapshot else None,
                        "price_lines": lines,
                    },
                    "availability": availability_by_model.get(model.public_model_code),
                }
            )

        items.sort(
            key=lambda item: (
                _CATEGORY_ORDER.get(item["category"], 99),
                _RELEASE_ORDER.get(item["category"], {}).get(item["model_code"], 999),
                str(item["display_name"]).lower(),
                item["model_code"],
            )
        )
        return items
