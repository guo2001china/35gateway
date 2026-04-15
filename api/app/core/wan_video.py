from __future__ import annotations

from typing import Any


WAN_VIDEO_DEFAULT_SIZE = "1280*720"

WAN_VIDEO_SIZE_MAP: dict[tuple[str, str], str] = {
    ("720P", "16:9"): "1280*720",
    ("720P", "9:16"): "720*1280",
    ("720P", "1:1"): "960*960",
    ("1080P", "16:9"): "1920*1080",
    ("1080P", "9:16"): "1080*1920",
    ("1080P", "1:1"): "1440*1440",
}

WAN_VIDEO_SIZE_TO_RESOLUTION: dict[str, str] = {
    value: resolution
    for (resolution, _aspect_ratio), value in WAN_VIDEO_SIZE_MAP.items()
}


def _first_non_empty(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def normalize_wan_reference_urls(payload: dict[str, Any]) -> list[str]:
    raw_value = _first_non_empty(payload, "reference_urls", "referenceUrls")
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value] if raw_value else []
    if isinstance(raw_value, (list, tuple)):
        normalized: list[str] = []
        for item in raw_value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    return []


def detect_wan_video_input_mode(payload: dict[str, Any]) -> str:
    reference_urls = normalize_wan_reference_urls(payload)
    input_reference = _first_non_empty(
        payload,
        "input_reference",
        "image_url",
        "image",
        "img_url",
        "first_frame",
        "firstFrame",
    )
    has_reference_urls = bool(reference_urls)
    has_input_reference = input_reference is not None

    if has_reference_urls and has_input_reference:
        return "invalid_mixed_references"
    if has_reference_urls:
        return "reference"
    if has_input_reference:
        return "image"
    return "text"


def canonicalize_wan_video_size(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("x", "*")
    alias_map = {
        "1280*720": "1280*720",
        "720*1280": "720*1280",
        "960*960": "960*960",
        "1920*1080": "1920*1080",
        "1080*1920": "1080*1920",
        "1440*1440": "1440*1440",
    }
    return alias_map.get(normalized)


def resolve_wan_video_size(payload: dict[str, Any], *, default: str = WAN_VIDEO_DEFAULT_SIZE) -> str | None:
    explicit_size = canonicalize_wan_video_size(payload.get("size"))
    if explicit_size is not None:
        return explicit_size

    resolution = str(payload.get("resolution") or "720P").upper()
    aspect_ratio = str(payload.get("aspect_ratio") or "16:9")
    if payload.get("resolution") is None and payload.get("aspect_ratio") is None:
        return default
    return WAN_VIDEO_SIZE_MAP.get((resolution, aspect_ratio))


def extract_wan_video_resolution_key(payload: dict[str, Any], *, default: str = "720P") -> str:
    size = resolve_wan_video_size(payload, default=WAN_VIDEO_DEFAULT_SIZE)
    if size is None:
        return default
    return WAN_VIDEO_SIZE_TO_RESOLUTION.get(size, default)


def resolve_wan_video_upstream_model(public_model_code: str, payload: dict[str, Any]) -> str | None:
    input_mode = detect_wan_video_input_mode(payload)
    if input_mode == "invalid_mixed_references":
        return None

    normalized_model = str(public_model_code)
    if normalized_model == "wan2.6":
        if input_mode == "text":
            return "wan2.6-t2v"
        if input_mode == "image":
            return "wan2.6-i2v"
        if input_mode == "reference":
            return "wan2.6-r2v"
        return None

    if normalized_model == "wan2.6-flash":
        if input_mode == "image":
            return "wan2.6-i2v-flash"
        if input_mode == "reference":
            return "wan2.6-r2v-flash"
        return None

    return None
