from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, COMMON_ESTIMATE_ERROR_RESPONSES
from app.api.params import ChainHeader, FallbackHeader, MetricsWindowHeader
from app.api.schemas import SeedanceRequest, VideoTaskResponse
from app.core.provider_support import detect_seedance_input_mode
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()

SEEDANCE_ROUTE_GROUP = "seedance"


def _build_create_invoke_ctx(
    provider,
    route_result,
    request_payload: dict[str, object],
    *,
    end_user_id: str,
) -> dict[str, object]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": SEEDANCE_ROUTE_GROUP,
        "payload": request_payload,
        "end_user_id": end_user_id,
        "method": "POST",
    }


def _build_response(task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    return response_body


def _validate_seedance_request(*, payload: dict[str, Any]) -> None:
    input_mode = detect_seedance_input_mode(payload)
    seconds = payload.get("seconds")
    if input_mode == "text" and not payload.get("prompt"):
        raise HTTPException(status_code=422, detail="prompt_required_for_text_mode")
    if seconds is not None and (int(seconds) < 4 or int(seconds) > 15):
        raise HTTPException(status_code=422, detail="seconds_out_of_range")


async def _create_seedance(
    *,
    payload: SeedanceRequest,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    fixed_model_code: str,
    chain: str | None,
    fallback: bool | None,
    metrics_window: str | None,
) -> dict[str, object]:
    payload_data = payload.model_dump(exclude_none=True)
    _validate_seedance_request(payload=payload_data)

    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group=SEEDANCE_ROUTE_GROUP,
        fixed_model_code=fixed_model_code,
        payload=payload_data,
        chain=chain,
        fallback=fallback,
        create_invoke_builder=lambda provider, route_result, request_payload: _build_create_invoke_ctx(
            provider,
            route_result,
            request_payload,
            end_user_id=f"user-{ctx.user_id}",
        ),
        response_builder=_build_response,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/seedance-2.0",
    summary="创建 Seedance 2.0 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_seedance20(
    payload: SeedanceRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_seedance(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="seedance-2.0",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )


@router.post(
    "/v1/seedance-2.0-fast",
    summary="创建 Seedance 2.0 Fast 视频任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_seedance20_fast(
    payload: SeedanceRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
    metrics_window: MetricsWindowHeader = None,
) -> dict[str, object]:
    return await _create_seedance(
        payload=payload,
        http_request=http_request,
        ctx=ctx,
        db=db,
        fixed_model_code="seedance-2.0-fast",
        chain=chain,
        fallback=fallback,
        metrics_window=metrics_window,
    )
