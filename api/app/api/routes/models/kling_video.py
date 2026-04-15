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
from app.api.schemas import KlingVideoRequest, VideoTaskResponse
from app.core.kling_video import (
    detect_kling_video_input_mode,
    normalize_kling_reference_images,
    resolve_kling_video_duration,
)
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()

KLING_VIDEO_ROUTE_GROUP = "kling_video"
KLING_VIDEO_CREATE_PATH = "/v1/videos/omni-video"


def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, object]) -> dict[str, object]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": KLING_VIDEO_ROUTE_GROUP,
        "path": KLING_VIDEO_CREATE_PATH,
        "payload": request_payload,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


def _validate_kling_video_request(payload: dict[str, Any]) -> None:
    input_mode = detect_kling_video_input_mode(payload)
    prompt = str(payload.get("prompt") or "").strip()
    seconds = resolve_kling_video_duration(payload)
    reference_images = normalize_kling_reference_images(payload)

    if not prompt:
        raise HTTPException(status_code=422, detail="prompt_required")
    if input_mode == "invalid_mixed_video_inputs":
        raise HTTPException(status_code=422, detail="mixed_video_inputs_not_allowed")
    if input_mode == "invalid_mixed_image_inputs":
        raise HTTPException(status_code=422, detail="mixed_image_inputs_not_allowed")
    if input_mode == "invalid_last_frame":
        raise HTTPException(status_code=422, detail="first_frame_required_for_last_frame")
    if seconds not in {5, 10}:
        raise HTTPException(status_code=422, detail="invalid_duration")

    raw_mode = payload.get("mode")
    if raw_mode is not None and str(raw_mode).strip().lower() not in {"std", "pro"}:
        raise HTTPException(status_code=422, detail="invalid_mode")

    if payload.get("generate_audio") is not None:
        raise HTTPException(status_code=422, detail="generate_audio_not_supported")

    if input_mode == "reference_images" and len(reference_images) > 7:
        raise HTTPException(status_code=422, detail="too_many_reference_images")


async def _create_kling_video(
    *,
    payload: KlingVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    chain: str | None,
    fallback: bool | None,
    metrics_window: str | None,
) -> dict[str, object]:
    payload_data = payload.model_dump(exclude_none=True)
    _validate_kling_video_request(payload_data)

    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group=KLING_VIDEO_ROUTE_GROUP,
        fixed_model_code="kling-o1",
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/kling-o1",
    summary="创建 Kling O1 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_kling_o1_video(
    payload: KlingVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_kling_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )
