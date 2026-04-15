from __future__ import annotations

from decimal import Decimal
import json
from typing import Any


VIDU_ROUTE_GROUP = "vidu"
VIDU_SUPPORTED_MODES = frozenset({"text", "image", "start_end"})
VIDU_Q3_MODELS = frozenset({"viduq3-pro", "viduq3-turbo"})
VIDU_Q3_RESOLUTIONS = frozenset({"540p", "720p", "1080p"})
VIDU_Q3_DEFAULT_DURATION = 5
VIDU_Q3_DEFAULT_RESOLUTION = "720p"
VIDU_CREDIT_COST_CNY = Decimal("0.03125")

VIDU_Q3_CREDITS_PER_SECOND: dict[str, dict[str, Decimal]] = {
    "viduq3-pro": {
        "540p": Decimal("10"),
        "720p": Decimal("25"),
        "1080p": Decimal("30"),
    },
    "viduq3-turbo": {
        "540p": Decimal("8"),
        "720p": Decimal("12"),
        "1080p": Decimal("14"),
    },
}
VIDU_Q3_OFF_PEAK_CREDITS_PER_SECOND: dict[str, dict[str, Decimal]] = {
    "viduq3-pro": {
        "540p": Decimal("5"),
        "720p": Decimal("13"),
        "1080p": Decimal("15"),
    },
    "viduq3-turbo": {
        "540p": Decimal("4"),
        "720p": Decimal("6"),
        "1080p": Decimal("7"),
    },
}


def normalize_vidu_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in VIDU_SUPPORTED_MODES else ""


def detect_vidu_input_mode(payload: dict[str, Any]) -> str:
    mode = normalize_vidu_mode(payload.get("mode"))
    if mode:
        return mode

    images = payload.get("images")
    if isinstance(images, list):
        if len(images) == 1:
            return "image"
        if len(images) == 2:
            return "start_end"
    return "text"


def normalize_vidu_images(payload: dict[str, Any]) -> list[str]:
    raw_images = payload.get("images")
    if not isinstance(raw_images, list):
        return []
    images: list[str] = []
    for item in raw_images:
        text = str(item or "").strip()
        if text:
            images.append(text)
    return images


def resolve_vidu_duration(payload: dict[str, Any], *, default: int = VIDU_Q3_DEFAULT_DURATION) -> int:
    raw_value = payload.get("duration")
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed


def resolve_vidu_resolution(payload: dict[str, Any], *, default: str = VIDU_Q3_DEFAULT_RESOLUTION) -> str:
    value = str(payload.get("resolution") or default).strip().lower()
    return value if value in VIDU_Q3_RESOLUTIONS else default


def resolve_vidu_audio_enabled(payload: dict[str, Any], *, default: bool = True) -> bool:
    raw_value = payload.get("audio")
    if raw_value is None:
        return default
    return bool(raw_value)


def quote_vidu_q3_credits(*, model_code: str, payload: dict[str, Any]) -> Decimal:
    resolution = resolve_vidu_resolution(payload)
    duration = resolve_vidu_duration(payload)
    off_peak = bool(payload.get("off_peak"))
    table = VIDU_Q3_OFF_PEAK_CREDITS_PER_SECOND if off_peak else VIDU_Q3_CREDITS_PER_SECOND
    credits_per_second = table.get(model_code, {}).get(resolution, Decimal("0"))
    credits = credits_per_second * Decimal(duration)
    if bool(payload.get("is_rec")):
        credits += Decimal("10")
    return credits


def build_vidu_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    request_payload: dict[str, Any] = {
        "model": payload["model"],
    }
    for key in (
        "prompt",
        "style",
        "duration",
        "seed",
        "aspect_ratio",
        "resolution",
        "movement_amplitude",
        "bgm",
        "audio",
        "audio_type",
        "voice_id",
        "is_rec",
        "off_peak",
        "watermark",
        "wm_position",
        "wm_url",
        "payload",
        "callback_url",
    ):
        value = payload.get(key)
        if value is not None:
            request_payload[key] = value

    images = normalize_vidu_images(payload)
    if images:
        request_payload["images"] = images

    meta_data = payload.get("meta_data")
    if meta_data is not None:
        request_payload["meta_data"] = json.dumps(meta_data, ensure_ascii=False) if isinstance(meta_data, dict) else meta_data

    return request_payload


def sanitize_vidu_payload_for_logging(payload: dict[str, Any]) -> dict[str, Any]:
    def _sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): _sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("data:") and ";base64," in stripped:
                header, encoded = stripped.split(";base64,", 1)
                mime_type = header.split(":", 1)[1] if ":" in header else "application/octet-stream"
                return f"[base64_omitted mime={mime_type} chars={len(encoded)}]"
            if len(stripped) > 4096:
                return f"{stripped[:512]}...[truncated chars={len(stripped)}]"
            return value
        return value

    return {str(key): _sanitize(value) for key, value in payload.items()}
