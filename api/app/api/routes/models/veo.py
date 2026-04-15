from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, COMMON_ESTIMATE_ERROR_RESPONSES
from app.api.params import (
    FallbackHeader,
    MetricsWindowHeader,
    ChainHeader,
)
from app.api.schemas import VeoRequest, VideoTaskResponse
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()


# Veo 创建路由只定义固定公开模型入口，具体供应商选择仍由下游动态决策。
def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, object]) -> dict[str, object]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "payload": request_payload,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


@router.post(
    "/v1/veo-3",
    summary="创建 Veo 3 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_veo3(
    payload: VeoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    """创建 Veo 3 视频任务。"""
    payload_data = payload.model_dump(exclude_none=True)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="veo3",
        fixed_model_code="veo-3",
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/veo-3-fast",
    summary="创建 Veo 3 Fast 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_veo3_fast(
    payload: VeoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    """创建 Veo 3 Fast 视频任务。"""
    payload_data = payload.model_dump(exclude_none=True)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="veo3",
        fixed_model_code="veo-3-fast",
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/veo-3.1",
    summary="创建 Veo 3.1 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_veo31(
    payload: VeoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    """创建 Veo 3.1 视频任务。"""
    payload_data = payload.model_dump(exclude_none=True)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="veo31",
        fixed_model_code="veo-3.1",
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/veo-3.1-fast",
    summary="创建 Veo 3.1 Fast 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_veo31_fast(
    payload: VeoRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    """创建 Veo 3.1 Fast 视频任务。"""
    payload_data = payload.model_dump(exclude_none=True)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="veo31",
        fixed_model_code="veo-3.1-fast",
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_response,
        metrics_window=metrics_window,
    )
