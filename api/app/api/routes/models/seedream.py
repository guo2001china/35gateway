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
from app.api.schemas import ImageGenerationResponse, SeedreamLiteRequest, SeedreamRequest
from app.domains.platform.services.proxy_execution import execute_proxy_request

router = APIRouter(prefix="/v1")


async def _execute_seedream_request(
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
        route_group="seedream",
        requested_model=model_code,
        provider_path="/images/generations",
        payload=payload,
        chain=chain,
        allow_fallback=allow_fallback,
    )


@router.post(
    "/doubao-seedream-4.5",
    summary="创建 Doubao Seedream 4.5 图片",
    response_model=ImageGenerationResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def doubao_seedream_4_5(
    payload: SeedreamRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """使用火山引擎 Doubao Seedream 4.5 创建图片。"""
    return await _execute_seedream_request(
        model_code="doubao-seedream-4.5",
        payload=payload.model_dump(exclude_none=True),
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
    )


@router.post(
    "/doubao-seedream-5.0-lite",
    summary="创建 Doubao Seedream 5.0 Lite 图片",
    response_model=ImageGenerationResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def doubao_seedream_5_0_lite(
    payload: SeedreamLiteRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """使用火山引擎 Doubao Seedream 5.0 Lite 创建图片。"""
    return await _execute_seedream_request(
        model_code="doubao-seedream-5.0-lite",
        payload=payload.model_dump(exclude_none=True),
        http_request=http_request,
        ctx=ctx,
        db=db,
        chain=chain,
        fallback=fallback,
    )
