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
from app.api.schemas import (
    GeminiGenerateContentRequest,
    GeminiGenerateContentResponse,
)
from app.domains.platform.services.proxy_execution import execute_proxy_request

router = APIRouter(prefix="/google")


@router.post(
    "/v1beta/models/{model}:generateContent",
    summary="创建 Gemini generateContent 响应",
    response_model=GeminiGenerateContentResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def google_generate_content(
    model: str,
    payload: GeminiGenerateContentRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """按路径参数中的 Gemini 模型代理 generateContent 请求。"""
    payload_data = payload.model_dump(exclude_none=True)
    allow_fallback = True if fallback is None else fallback
    return await execute_proxy_request(
        http_request=http_request,
        ctx=ctx,
        db=db,
        route_group="gemini",
        requested_model=model,
        provider_path=f"/v1beta/models/{model}:generateContent",
        payload=payload_data,
        chain=chain,
        allow_fallback=allow_fallback,
    )
