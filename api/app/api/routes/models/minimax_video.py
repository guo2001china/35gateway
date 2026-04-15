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
from app.api.schemas import MiniMaxVideoRequest, VideoTaskResponse
from app.core.provider_support import detect_minimax_video_input_mode
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()

MINIMAX_VIDEO_ROUTE_GROUP = "minimax_video"
MINIMAX_VIDEO_CREATE_PATH = "/v1/video_generation"


def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, object]) -> dict[str, object]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": MINIMAX_VIDEO_ROUTE_GROUP,
        "path": MINIMAX_VIDEO_CREATE_PATH,
        "payload": request_payload,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


def _validate_minimax_video_request(*, model_code: str, payload: dict[str, Any]) -> None:
    input_mode = detect_minimax_video_input_mode(payload)
    if input_mode == "invalid_last_frame":
        raise HTTPException(status_code=422, detail="first_frame_required")
    if input_mode == "text" and not payload.get("prompt"):
        raise HTTPException(status_code=422, detail="prompt_required_for_text_mode")
    if model_code == "MiniMax-Hailuo-2.3-Fast" and input_mode != "image":
        raise HTTPException(status_code=422, detail="image_required_for_model")
    if model_code == "minimax-hailuo-2.3-fast" and input_mode != "image":
        raise HTTPException(status_code=422, detail="image_required_for_model")
    if input_mode == "first_last_frame" and model_code not in {"MiniMax-Hailuo-02", "minimax-hailuo-02"}:
        raise HTTPException(status_code=422, detail="first_last_frame_not_supported")


async def _create_minimax_video(
    *,
    payload: MiniMaxVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    fixed_model_code: str,
    chain: str | None,
    fallback: bool | None,
    metrics_window: str | None,
) -> dict[str, object]:
    payload_data = payload.model_dump(exclude_none=True)
    _validate_minimax_video_request(model_code=fixed_model_code, payload=payload_data)

    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group=MINIMAX_VIDEO_ROUTE_GROUP,
        fixed_model_code=fixed_model_code,
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/minimax-hailuo-2.3",
    summary="创建 MiniMax Hailuo 2.3 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_minimax_hailuo_23(
    payload: MiniMaxVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_minimax_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="minimax-hailuo-2.3",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/minimax-hailuo-2.3-fast",
    summary="创建 MiniMax Hailuo 2.3 Fast 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_minimax_hailuo_23_fast(
    payload: MiniMaxVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_minimax_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="minimax-hailuo-2.3-fast",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/minimax-hailuo-02",
    summary="创建 MiniMax Hailuo 02 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_minimax_hailuo_02(
    payload: MiniMaxVideoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_minimax_video(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="minimax-hailuo-02",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )
