from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, COMMON_ESTIMATE_ERROR_RESPONSES
from app.api.params import (
    FallbackHeader,
    ChainHeader,
)
from app.api.schemas import BananaRequest, ImageGenerationResponse
from app.domains.platform.services.proxy_execution import execute_proxy_request

router = APIRouter(prefix="/v1")


# Banana 当前走同步代理链路；正式创建和请求前预计费共用同一路由入口。
async def _execute_banana_request(
    *,
    model_code: str,
    payload: dict[str, object],
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    chain: str | None,
    fallback: bool | None,
) -> dict[str, Any]:
    allow_fallback = True if fallback is None else fallback
    return await execute_proxy_request(
        http_request=http_request,
        ctx=ctx,
        db=db,
        route_group="banana",
        requested_model=model_code,
        provider_path=f"/v1beta/models/{model_code}:generateContent",
        payload=payload,
        chain=chain,
        allow_fallback=allow_fallback,
    )


@router.post(
    "/nano-banana",
    summary="创建 Nano Banana 图片",
    response_model=ImageGenerationResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def nano_banana(
    payload: BananaRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """使用基础版 Nano Banana 创建或编辑图片。"""
    return await _execute_banana_request(
        model_code="nano-banana",
        payload=payload.model_dump(exclude_none=True),
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
    )


@router.post(
    "/nano-banana-pro",
    summary="创建 Nano Banana Pro 图片",
    response_model=ImageGenerationResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def nano_banana_pro(
    payload: BananaRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """使用 Nano Banana Pro 创建或编辑图片。"""
    return await _execute_banana_request(
        model_code="nano-banana-pro",
        payload=payload.model_dump(exclude_none=True),
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
    )


@router.post(
    "/nano-banana-2",
    summary="创建 Nano Banana 2 图片",
    response_model=ImageGenerationResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def nano_banana_2(
    payload: BananaRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """使用 Nano Banana 2 创建或编辑图片。"""
    return await _execute_banana_request(
        model_code="nano-banana-2",
        payload=payload.model_dump(exclude_none=True),
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
    )
