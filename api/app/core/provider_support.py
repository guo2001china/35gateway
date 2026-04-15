from __future__ import annotations

from typing import Any

from app.core.kling_video import detect_kling_video_input_mode
from app.core.vidu_video import detect_vidu_input_mode
from app.core.wan_video import detect_wan_video_input_mode


def _first_non_empty(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def detect_veo_input_mode(payload: dict[str, Any]) -> str:
    video_input = _first_non_empty(payload, "video", "video_url")
    if video_input is not None:
        return "extend_video"

    reference_images = _first_non_empty(payload, "reference_images", "referenceImages", "image_urls")
    if reference_images:
        return "reference_images"

    first_frame = _first_non_empty(
        payload,
        "first_frame",
        "firstFrame",
        "first_frame_url",
        "input_reference",
        "image_url",
        "image",
    )
    last_frame = _first_non_empty(payload, "last_frame", "lastFrame", "last_frame_url")
    if first_frame is not None and last_frame is not None:
        return "first_last_frame"

    image_input = _first_non_empty(payload, "input_reference", "image_url", "image")
    if image_input is not None:
        return "image"

    return "text"


def detect_banana_input_mode(payload: dict[str, Any]) -> str:
    image_urls = _first_non_empty(payload, "image_urls", "input_images")
    if image_urls:
        return "edit"
    return "text"


def detect_seedance_input_mode(payload: dict[str, Any]) -> str:
    image_input = _first_non_empty(
        payload,
        "input_reference",
        "image_url",
        "image",
    )
    if image_input is not None:
        return "image"
    return "text"


def detect_minimax_video_input_mode(payload: dict[str, Any]) -> str:
    first_frame = _first_non_empty(
        payload,
        "first_frame",
        "firstFrame",
        "first_frame_image",
        "input_reference",
        "image_url",
        "image",
    )
    last_frame = _first_non_empty(payload, "last_frame", "lastFrame", "last_frame_image")

    if last_frame is not None and first_frame is None:
        return "invalid_last_frame"
    if first_frame is not None and last_frame is not None:
        return "first_last_frame"
    if first_frame is not None:
        return "image"
    return "text"


def provider_supports_payload(
    *,
    route_group: str,
    provider_code: str,
    model_code: str,
    payload: dict[str, Any],
) -> bool:
    if route_group == "banana":
        mode = detect_banana_input_mode(payload)
        if provider_code == "google_official":
            return model_code in {
                "gemini-2.5-flash-image",
                "gemini-3-pro-image-preview",
                "gemini-3.1-flash-image-preview",
            } and mode in {"text", "edit"}
        if provider_code == "fal_nano_banana":
            return mode in {"text", "edit"}
        if provider_code == "grsai_nano_banana":
            return mode in {"text", "edit"}
        return True

    if route_group == "seedance":
        mode = detect_seedance_input_mode(payload)
        if provider_code == "fal_seedance20":
            return model_code in {"seedance-2.0", "seedance-2.0-fast"} and mode in {"text", "image"}
        return True

    if route_group == "minimax_video":
        mode = detect_minimax_video_input_mode(payload)
        if mode == "invalid_last_frame":
            return False
        if provider_code == "minimax_official":
            if model_code == "MiniMax-Hailuo-2.3":
                return mode in {"text", "image"}
            if model_code == "MiniMax-Hailuo-2.3-Fast":
                return mode in {"image"}
            if model_code == "MiniMax-Hailuo-02":
                return mode in {"text", "image", "first_last_frame"}
        return True

    if route_group == "wan_video":
        mode = detect_wan_video_input_mode(payload)
        if mode == "invalid_mixed_references":
            return False
        if provider_code == "wan_official":
            if model_code == "wan2.6":
                return mode in {"text", "image", "reference"}
            if model_code == "wan2.6-flash":
                return mode in {"image", "reference"}
        return True

    if route_group == "kling_video":
        mode = detect_kling_video_input_mode(payload)
        if mode in {"invalid_last_frame", "invalid_mixed_image_inputs", "invalid_mixed_video_inputs"}:
            return False
        if provider_code == "kling_official" and model_code == "kling-o1":
            return mode in {"text", "image", "reference_images", "video_reference", "first_last_frame"}
        return True

    if route_group == "vidu":
        mode = detect_vidu_input_mode(payload)
        if provider_code == "vidu_official" and model_code in {"viduq3-pro", "viduq3-turbo"}:
            return mode in {"text", "image", "start_end"}
        return True

    if route_group == "veo3":
        mode = detect_veo_input_mode(payload)
        resolution = str(payload.get("resolution") or "720p").lower()
        if provider_code == "fal_veo3":
            if model_code in {"veo-3", "veo-3-fast"}:
                return mode in {"text", "image"} and resolution in {"720p", "1080p"}
        return True

    if route_group != "veo31":
        return True

    mode = detect_veo_input_mode(payload)

    if provider_code == "fal_veo31":
        if model_code == "veo-3.1-generate-preview":
            return mode in {"text", "image", "first_last_frame", "reference_images"}
        if model_code == "veo-3.1-fast-generate-preview":
            return mode in {"text", "image", "first_last_frame", "extend_video"}

    return True
