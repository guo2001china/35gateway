from __future__ import annotations

from typing import Any


def _first_non_empty(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def normalize_kling_reference_images(payload: dict[str, Any]) -> list[str]:
    raw_value = _first_non_empty(payload, "reference_images", "referenceImages")
    if not isinstance(raw_value, list):
        return []
    return [str(item).strip() for item in raw_value if str(item).strip()]


def detect_kling_video_input_mode(payload: dict[str, Any]) -> str:
    video_url = _first_non_empty(payload, "video_url", "video")
    input_reference = _first_non_empty(payload, "input_reference", "image_url", "image")
    first_frame = _first_non_empty(payload, "first_frame", "firstFrame", "first_frame_url")
    last_frame = _first_non_empty(payload, "last_frame", "lastFrame", "last_frame_url")
    reference_images = normalize_kling_reference_images(payload)

    if video_url is not None:
        if input_reference is not None or first_frame is not None or last_frame is not None or reference_images:
            return "invalid_mixed_video_inputs"
        return "video_reference"

    if last_frame is not None and first_frame is None:
        return "invalid_last_frame"

    if first_frame is not None:
        if input_reference is not None or reference_images:
            return "invalid_mixed_image_inputs"
        if last_frame is not None:
            return "first_last_frame"
        return "image"

    if input_reference is not None:
        if reference_images:
            return "invalid_mixed_image_inputs"
        return "image"

    if reference_images:
        return "reference_images"

    return "text"


def resolve_kling_video_mode(payload: dict[str, Any], *, default: str = "pro") -> str:
    mode = str(payload.get("mode") or default).strip().lower()
    return mode if mode in {"std", "pro"} else default


def resolve_kling_video_duration(payload: dict[str, Any], *, default: int = 5) -> int:
    raw_value = payload.get("seconds", payload.get("duration"))
    if raw_value is None:
        return default
    if isinstance(raw_value, str) and raw_value.endswith("s"):
        raw_value = raw_value[:-1]
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed


def resolve_kling_upstream_model(model_code: str) -> str | None:
    if model_code in {"kling-o1", "kling-video-o1"}:
        return "kling-video-o1"
    return None
