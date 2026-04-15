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
from app.api.schemas import VideoTaskResponse, WanVideoRequest
from app.core.wan_video import detect_wan_video_input_mode, normalize_wan_reference_urls, resolve_wan_video_size
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()

WAN_VIDEO_ROUTE_GROUP = "wan_video"
WAN_VIDEO_CREATE_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"


def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, object]) -> dict[str, object]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": WAN_VIDEO_ROUTE_GROUP,
        "path": WAN_VIDEO_CREATE_PATH,
        "payload": request_payload,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


def _validate_wan_video_request(*, model_code: str, payload: dict[str, Any]) -> None:
    input_mode = detect_wan_video_input_mode(payload)
    shot_type = payload.get("shot_type")
    if input_mode == "invalid_mixed_references":
        raise HTTPException(status_code=422, detail="mixed_reference_inputs_not_allowed")
    if input_mode == "text" and not payload.get("prompt"):
        raise HTTPException(status_code=422, detail="prompt_required_for_text_mode")
    if model_code == "wan2.6-flash" and input_mode == "text":
        raise HTTPException(status_code=422, detail="text_not_supported_for_model")
    if shot_type is not None and input_mode != "reference":
        raise HTTPException(status_code=422, detail="shot_type_only_supported_for_reference_mode")
    if shot_type is not None and shot_type not in {"single", "multi"}:
        raise HTTPException(status_code=422, detail="invalid_shot_type")
    if payload.get("generate_audio") is False and model_code == "wan2.6":
        raise HTTPException(status_code=422, detail="silent_video_not_supported_for_model")
    if payload.get("audio_url") is not None and payload.get("generate_audio") is False:
        raise HTTPException(status_code=422, detail="audio_url_conflicts_with_silent_mode")
    if len(normalize_wan_reference_urls(payload)) > 5:
        raise HTTPException(status_code=422, detail="too_many_reference_urls")
    if resolve_wan_video_size(payload) is None:
        raise HTTPException(status_code=422, detail="invalid_size_or_resolution")


async def _create_wan_video(
    *,
    payload: WanVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    fixed_model_code: str,
    chain: str | None,
    fallback: bool | None,
    metrics_window: str | None,
) -> dict[str, object]:
    payload_data = payload.model_dump(exclude_none=True)
    _validate_wan_video_request(model_code=fixed_model_code, payload=payload_data)

    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group=WAN_VIDEO_ROUTE_GROUP,
        fixed_model_code=fixed_model_code,
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/wan2.6",
    summary="创建 Wan 2.6 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_wan26_video(
    payload: WanVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_wan_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="wan2.6",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/wan2.6-flash",
    summary="创建 Wan 2.6 Flash 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_wan26_flash_video(
    payload: WanVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_wan_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="wan2.6-flash",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )
