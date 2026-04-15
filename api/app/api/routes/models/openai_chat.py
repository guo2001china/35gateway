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
    OpenAIChatCompletionsRequest,
    OpenAIChatCompletionsResponse,
)
from app.domains.platform.services.proxy_execution import execute_proxy_request

router = APIRouter(prefix="/v1")


@router.post(
    "/chat/completions",
    summary="创建 OpenAI 兼容聊天响应",
    response_model=OpenAIChatCompletionsResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def openai_chat_completions(
    payload: OpenAIChatCompletionsRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    chain: ChainHeader = None,
    fallback: FallbackHeader = None,
) -> dict[str, Any]:
    """按平台选定的文本模型代理 OpenAI 兼容聊天请求。"""
    payload_data = payload.model_dump(exclude_none=True)
    allow_fallback = True if fallback is None else fallback
    return await execute_proxy_request(
        http_request=http_request,
        ctx=ctx,
        db=db,
        route_group="openai",
        requested_model=payload_data.get("model"),
        provider_path="/v1/chat/completions",
        payload=payload_data,
        chain=chain,
        allow_fallback=allow_fallback,
    )
