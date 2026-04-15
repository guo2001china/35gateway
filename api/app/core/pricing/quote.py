from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.pricing.audio import (
    quote_minimax_t2a_async_request,
    quote_qwen_tts_request,
    quote_qwen_voice_clone_request,
)
from app.core.pricing.common import CNY, ZERO, empty_snapshot
from app.core.pricing.image import quote_banana_request, quote_seedream_request
from app.core.pricing.text import finalize_text_billing_snapshot, quote_text_request
from app.core.pricing.video import (
    quote_kling_video_request,
    quote_minimax_video_request,
    quote_seedance_request,
    quote_veo_request,
    quote_vidu_video_request,
    quote_wan_video_request,
)
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot


def quote_request(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    pricing_strategy: str,
    public_model_code: str,
    payload: dict[str, Any],
) -> tuple[Decimal, str, dict[str, Any]]:
    model = get_platform_config_snapshot().get_model(public_model_code)
    model_code = model.public_model_code
    billing_unit = model.billing_unit
    if pricing_strategy == "text_tokens":
        return quote_text_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_veo":
        return quote_veo_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_seedance":
        return quote_seedance_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_minimax":
        return quote_minimax_video_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_wan":
        return quote_wan_video_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_kling":
        return quote_kling_video_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "video_vidu":
        return quote_vidu_video_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "image_seedream":
        return quote_seedream_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy in {"image_banana_fixed", "image_banana_fixed_resolution"}:
        return quote_banana_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "audio_qwen_tts":
        return quote_qwen_tts_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "audio_qwen_voice_clone":
        return quote_qwen_voice_clone_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    if pricing_strategy == "audio_minimax_t2a":
        return quote_minimax_t2a_async_request(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            payload=payload,
        )

    return ZERO, CNY, empty_snapshot(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        billing_unit=billing_unit,
    )


def finalize_billing_snapshot(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    pricing_strategy: str,
    public_model_code: str,
    response_payload: dict[str, Any],
    estimated_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    model = get_platform_config_snapshot().get_model(public_model_code)
    model_code = model.public_model_code
    billing_unit = model.billing_unit
    if pricing_strategy == "text_tokens":
        return finalize_text_billing_snapshot(
            provider_code=provider_code,
            route_group=route_group,
            execution_model_code=execution_model_code,
            model_code=model_code,
            public_model_code=public_model_code,
            billing_unit=billing_unit,
            response_payload=response_payload,
            estimated_snapshot=estimated_snapshot,
        )
    return estimated_snapshot or empty_snapshot(
        provider_code=provider_code,
        route_group=route_group,
        model_code=model_code,
        billing_unit=billing_unit,
    )
