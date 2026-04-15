from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, COMMON_ESTIMATE_ERROR_RESPONSES
from app.api.params import (
    FallbackHeader,
    MetricsWindowHeader,
    ChainHeader,
)
from app.api.schemas import VideoTaskResponse, ViduVideoRequest
from app.core.vidu_video import VIDU_Q3_MODELS, detect_vidu_input_mode, normalize_vidu_images, resolve_vidu_audio_enabled
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()

VIDU_ROUTE_GROUP = "vidu"
_VIDU_CREATE_PATH_BY_MODE = {
    "text": "/ent/v2/text2video",
    "image": "/ent/v2/img2video",
    "start_end": "/ent/v2/start-end2video",
}


def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, object]) -> dict[str, object]:
    mode = detect_vidu_input_mode(request_payload)
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": VIDU_ROUTE_GROUP,
        "path": _VIDU_CREATE_PATH_BY_MODE[mode],
        "payload": request_payload,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


def _validate_vidu_video_request(*, model_code: str, payload: dict[str, Any]) -> None:
    if model_code not in VIDU_Q3_MODELS:
        raise HTTPException(status_code=422, detail="unsupported_model")

    mode = detect_vidu_input_mode(payload)
    if mode not in {"text", "image", "start_end"}:
        raise HTTPException(status_code=422, detail="unsupported_vidu_mode")

    duration = payload.get("duration")
    if duration is not None:
        try:
            duration_value = int(duration)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="invalid_duration") from None
        if duration_value < 1 or duration_value > 16:
            raise HTTPException(status_code=422, detail="duration_out_of_range")

    images = normalize_vidu_images(payload)
    if mode == "text":
        if not payload.get("prompt"):
            raise HTTPException(status_code=422, detail="prompt_required_for_text_mode")
        if images:
            raise HTTPException(status_code=422, detail="images_not_supported_for_text_mode")
        if payload.get("audio_type") is not None:
            raise HTTPException(status_code=422, detail="audio_type_not_supported_for_text_mode")
        if payload.get("voice_id") is not None:
            raise HTTPException(status_code=422, detail="voice_id_not_supported_for_text_mode")
        if payload.get("is_rec") is not None:
            raise HTTPException(status_code=422, detail="is_rec_not_supported_for_text_mode")

    if mode == "image":
        if len(images) != 1:
            raise HTTPException(status_code=422, detail="single_image_required_for_image_mode")
        if payload.get("aspect_ratio") is not None:
            raise HTTPException(status_code=422, detail="aspect_ratio_not_supported_for_image_mode")
        if payload.get("style") is not None:
            raise HTTPException(status_code=422, detail="style_not_supported_for_image_mode")

    if mode == "start_end":
        if len(images) != 2:
            raise HTTPException(status_code=422, detail="two_images_required_for_start_end_mode")
        if payload.get("aspect_ratio") is not None:
            raise HTTPException(status_code=422, detail="aspect_ratio_not_supported_for_start_end_mode")
        if payload.get("style") is not None:
            raise HTTPException(status_code=422, detail="style_not_supported_for_start_end_mode")
        if payload.get("audio_type") is not None:
            raise HTTPException(status_code=422, detail="audio_type_not_supported_for_start_end_mode")
        if payload.get("voice_id") is not None:
            raise HTTPException(status_code=422, detail="voice_id_not_supported_for_start_end_mode")

    if payload.get("audio") is False and payload.get("audio_type") is not None:
        raise HTTPException(status_code=422, detail="audio_type_requires_audio_enabled")

    if payload.get("off_peak") and not resolve_vidu_audio_enabled(payload):
        raise HTTPException(status_code=422, detail="off_peak_requires_audio_enabled")


async def _create_vidu_video(
    *,
    payload: ViduVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    fixed_model_code: str,
    chain: str | None,
    fallback: bool | None,
    metrics_window: str | None,
) -> dict[str, object]:
    payload_data = payload.model_dump(exclude_none=True)
    _validate_vidu_video_request(model_code=fixed_model_code, payload=payload_data)

    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group=VIDU_ROUTE_GROUP,
        fixed_model_code=fixed_model_code,
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/viduq3-pro",
    summary="创建 Vidu Q3 Pro 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_vidu_q3_pro_video(
    payload: ViduVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_vidu_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="viduq3-pro",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/viduq3-turbo",
    summary="创建 Vidu Q3 Turbo 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_vidu_q3_turbo_video(
    payload: ViduVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_vidu_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="viduq3-turbo",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )
