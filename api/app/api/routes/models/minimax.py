from __future__ import annotations

import httpx
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, UserAccessContext, require_api_key, require_user_access
from app.api.deps import get_db
from app.api.openapi_responses import (
    AUTH_ERROR_RESPONSES,
    COMMON_ESTIMATE_ERROR_RESPONSES,
    PROVIDER_API_ERROR_RESPONSES,
    TASK_NOT_FOUND_RESPONSE,
)
from app.api.schemas import (
    MiniMaxClonedTtsRequest,
    MiniMaxSystemTtsRequest,
    MiniMaxT2AAsyncTaskResponse,
    MiniMaxVoiceCatalogResponse,
    MiniMaxVoiceCloneRequest,
    MiniMaxVoiceCloneResponse,
    MiniMaxVoiceDeleteResponse,
)
from app.core.provider_catalog import get_provider
from app.domains.platform.entities.entities import Request as RequestLog
from app.domains.platform.entities.entities import Task
from app.domains.platform.providers.registry import get_adapter
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService, task_finished
from app.domains.platform.services.provider_api_execution import ProviderApiExecutionService

router = APIRouter(prefix="/v1/minimax")

MINIMAX_PROVIDER_CODE = "35m"
MINIMAX_DEFAULT_T2A_MODEL = "speech-2.8-hd"
MINIMAX_T2A_PATH = "/v1/t2a_async_v2"
MINIMAX_T2A_QUERY_PATH = "/v1/query/t2a_async_query_v2"
MINIMAX_VOICE_CLONE_PATH = "/v1/voice_clone"
MINIMAX_GET_VOICE_PATH = "/v1/get_voice"
MINIMAX_DELETE_VOICE_PATH = "/v1/delete_voice"
MINIMAX_SYSTEM_VOICE_TYPE = "system"
MINIMAX_CLONED_VOICE_TYPE = "voice_cloning"


def _using_35m_public_gateway() -> bool:
    return MINIMAX_PROVIDER_CODE == "35m"


def _get_task_by_platform_task_id(db: Session, platform_task_id: str, user_id: int) -> Task:
    task = (
        db.query(Task)
        .join(RequestLog, Task.request_id == RequestLog.id)
        .filter(Task.platform_task_id == platform_task_id, RequestLog.user_id == user_id)
        .order_by(Task.id.desc())
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


def _build_create_invoke_ctx(provider, route_result, request_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_model": route_result,
        "route_group": "minimax_t2a_async",
        "path": MINIMAX_T2A_PATH,
        "payload": request_payload,
        "method": "POST",
    }


def _build_query_invoke_ctx(provider, task: Task) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_model": task,
        "route_group": "minimax_t2a_async",
        "path": f"{MINIMAX_T2A_QUERY_PATH}?task_id={task.provider_task_id}",
        "method": "GET",
    }


def _build_content_ctx(provider, task: Task) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_model": task,
        "route_group": "minimax_t2a_async",
    }


def _build_task_response(
    task: Task,
    result: dict[str, Any],
    *,
    voice_id: str | None = None,
    voice_type: str | None = None,
) -> dict[str, Any]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body["model"] = task.public_model_code
    if voice_id is not None:
        response_body["voice_id"] = voice_id
    if voice_type is not None:
        response_body["voice_type"] = voice_type
    if response_body.get("created_at") is None:
        response_body["created_at"] = int(task.created_at.replace(tzinfo=timezone.utc).timestamp())
    return response_body


def _build_task_response_builder(*, voice_id: str, voice_type: str):
    def _response_builder(task: Task, result: dict[str, Any]) -> dict[str, Any]:
        return _build_task_response(task, result, voice_id=voice_id, voice_type=voice_type)

    return _response_builder


def _build_minimax_tts_payload(payload: MiniMaxSystemTtsRequest | MiniMaxClonedTtsRequest) -> dict[str, Any]:
    request_payload = payload.model_dump(exclude_none=True)
    voice_id = str(request_payload.pop("voice_id"))
    voice_setting = dict(request_payload.pop("voice_setting", {}) or {})
    request_payload["model"] = str(request_payload.get("model") or MINIMAX_DEFAULT_T2A_MODEL)
    request_payload["voice_setting"] = {
        "voice_id": voice_id,
        **voice_setting,
    }
    return request_payload


def _build_minimax_voice_clone_payload(payload: MiniMaxVoiceCloneRequest) -> dict[str, Any]:
    request_payload = payload.model_dump(exclude_none=True)
    request_payload["model"] = MINIMAX_DEFAULT_T2A_MODEL
    return request_payload


def _build_minimax_voice_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "voice_id": item.get("voice_id"),
        "voice_name": item.get("voice_name"),
        "description": item.get("description"),
        "created_time": item.get("created_time"),
    }


def _build_minimax_voice_catalog_response(
    upstream_response: dict[str, Any],
    *,
    source_key: str,
    voice_id: str | None,
    q: str | None,
    page_index: int,
    page_size: int,
) -> dict[str, Any]:
    normalized_voice_id = (voice_id or "").strip().lower()
    normalized_q = (q or "").strip().lower()

    items: list[dict[str, Any]] = []
    for raw_item in upstream_response.get(source_key) or []:
        if not isinstance(raw_item, dict):
            continue
        item = _build_minimax_voice_item(raw_item)
        current_voice_id = str(item.get("voice_id") or "").strip().lower()
        if normalized_voice_id and current_voice_id != normalized_voice_id:
            continue
        if normalized_q:
            searchable = " ".join(
                [
                    str(item.get("voice_id") or ""),
                    str(item.get("voice_name") or ""),
                    " ".join(item.get("description") or []),
                ]
            ).lower()
            if normalized_q not in searchable:
                continue
        items.append(item)

    total = len(items)
    start = page_index * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page_index": page_index,
        "page_size": page_size,
    }


def _build_minimax_voice_delete_response(*, voice_id: str) -> dict[str, Any]:
    return {
        "voice_id": voice_id,
        "deleted": True,
    }


async def _fetch_minimax_voice_catalog(*, voice_type: str) -> dict[str, Any]:
    provider = get_provider(MINIMAX_PROVIDER_CODE)
    adapter = get_adapter(provider.adapter_key)
    try:
        return await adapter.invoke(
            {
                "provider": provider,
                "route_group": "minimax_voice_clone",
                "path": MINIMAX_GET_VOICE_PATH,
                "payload": {"voice_type": voice_type},
                "method": "POST",
            }
        )
    except (httpx.HTTPError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="voice_lookup_failed") from exc


async def _fetch_minimax_voice_ids_for_validation(*, voice_type: str) -> set[str]:
    catalog = await _fetch_minimax_voice_catalog(voice_type=voice_type)
    source_key = "system_voice" if voice_type == MINIMAX_SYSTEM_VOICE_TYPE else "voice_cloning"
    return {
        str(item.get("voice_id"))
        for item in catalog.get(source_key) or []
        if isinstance(item, dict) and item.get("voice_id")
    }


async def _validate_minimax_system_tts_request(payload: MiniMaxSystemTtsRequest) -> None:
    if _using_35m_public_gateway():
        return
    voice_ids = await _fetch_minimax_voice_ids_for_validation(voice_type=MINIMAX_SYSTEM_VOICE_TYPE)
    if payload.voice_id not in voice_ids:
        raise HTTPException(status_code=422, detail="system_voice_required")


async def _validate_minimax_cloned_tts_request(payload: MiniMaxClonedTtsRequest) -> None:
    if _using_35m_public_gateway():
        return
    voice_ids = await _fetch_minimax_voice_ids_for_validation(voice_type=MINIMAX_CLONED_VOICE_TYPE)
    if payload.voice_id not in voice_ids:
        raise HTTPException(status_code=422, detail="cloned_voice_required")


@router.get(
    "/system-voices",
    summary="获取 MiniMax system voice 列表",
    response_model=MiniMaxVoiceCatalogResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def list_minimax_system_voices(
    http_request: Request,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
    voice_id: str | None = Query(default=None, description="按 `voice_id` 精确筛选。"),
    q: str | None = Query(default=None, description="按 `voice_id`、`voice_name`、描述做模糊搜索。"),
    page_index: int = Query(default=0, ge=0, le=1000000, description="页码索引。"),
    page_size: int = Query(default=20, ge=1, le=1000000, description="每页返回条数。"),
) -> dict[str, Any]:
    """返回当前 MiniMax 账号下可用的 system voice 目录。"""
    if _using_35m_public_gateway():
        return await ProviderApiExecutionService(db).execute(
            http_request=http_request,
            ctx=ctx,
            provider_code=MINIMAX_PROVIDER_CODE,
            route_group="minimax_voice_clone",
            model_code=MINIMAX_DEFAULT_T2A_MODEL,
            provider_path=MINIMAX_GET_VOICE_PATH,
            payload={
                key: value
                for key, value in {
                    "voice_id": voice_id,
                    "q": q,
                    "page_index": page_index,
                    "page_size": page_size,
                }.items()
                if value is not None
            },
            forward_payload={
                key: value
                for key, value in {
                    "voice_id": voice_id,
                    "q": q,
                    "page_index": page_index,
                    "page_size": page_size,
                }.items()
                if value is not None
            },
            bill_on_success=False,
            persist_request_log=False,
        )
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=MINIMAX_PROVIDER_CODE,
        route_group="minimax_voice_clone",
        model_code=MINIMAX_DEFAULT_T2A_MODEL,
        provider_path=MINIMAX_GET_VOICE_PATH,
        payload={"voice_type": MINIMAX_SYSTEM_VOICE_TYPE},
        bill_on_success=False,
        persist_request_log=False,
    )
    return _build_minimax_voice_catalog_response(
        upstream_response,
        source_key="system_voice",
        voice_id=voice_id,
        q=q,
        page_index=page_index,
        page_size=page_size,
    )


@router.post(
    "/system-tts",
    summary="创建 MiniMax system voice 异步语音任务",
    response_model=MiniMaxT2AAsyncTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_minimax_system_tts(
    payload: MiniMaxSystemTtsRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """按能力型公开契约创建 MiniMax system voice 异步语音任务。"""
    await _validate_minimax_system_tts_request(payload)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="minimax_t2a_async",
        fixed_model_code=payload.model,
        payload=_build_minimax_tts_payload(payload),
        forward_payload=payload.model_dump(exclude_none=True),
        chain=MINIMAX_PROVIDER_CODE,
        fallback=False,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_task_response_builder(
            voice_id=payload.voice_id,
            voice_type=MINIMAX_SYSTEM_VOICE_TYPE,
        ),
    )


@router.get(
    "/t2a-async/{task_id}",
    summary="查询 MiniMax 异步长文本语音任务",
    response_model=MiniMaxT2AAsyncTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **TASK_NOT_FOUND_RESPONSE},
)
async def get_minimax_t2a_async(
    task_id: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """查询当前用户创建的 MiniMax 语音任务。"""
    task = _get_task_by_platform_task_id(db, task_id, ctx.user_id)
    service = AsyncTaskExecutionService(db)
    return await service.get_task(
        http_request=http_request,
        ctx=ctx,
        task=task,
        route_group="minimax_t2a_async",
        task_invoke_builder=_build_query_invoke_ctx,
        response_builder=_build_task_response,
    )


@router.get(
    "/t2a-async/{task_id}/content",
    summary="下载 MiniMax 异步长文本语音结果",
    responses={**AUTH_ERROR_RESPONSES, **TASK_NOT_FOUND_RESPONSE},
)
async def get_minimax_t2a_async_content(
    task_id: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """下载当前用户已完成的 MiniMax 语音任务结果。"""
    task = _get_task_by_platform_task_id(db, task_id, ctx.user_id)
    service = AsyncTaskExecutionService(db)
    if not task_finished(task.status):
        await service.get_task(
            http_request=http_request,
            ctx=ctx,
            task=task,
            route_group="minimax_t2a_async",
            task_invoke_builder=_build_query_invoke_ctx,
            response_builder=_build_task_response,
        )
        task = _get_task_by_platform_task_id(db, task_id, ctx.user_id)
    return await service.download_content(
        http_request=http_request,
        ctx=ctx,
        task=task,
        route_group="minimax_t2a_async",
        task_content_builder=_build_content_ctx,
    )


@router.get(
    "/voice-clones",
    summary="获取 MiniMax cloned voice 列表",
    response_model=MiniMaxVoiceCatalogResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def list_minimax_voice_clones(
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    voice_id: str | None = Query(default=None, description="按 `voice_id` 精确筛选。"),
    q: str | None = Query(default=None, description="按 `voice_id`、`voice_name`、描述做模糊搜索。"),
    page_index: int = Query(default=0, ge=0, le=1000000, description="页码索引。"),
    page_size: int = Query(default=20, ge=1, le=1000000, description="每页返回条数。"),
) -> dict[str, Any]:
    """返回当前 MiniMax 账号下可用的 cloned voice 目录。"""
    if _using_35m_public_gateway():
        return await ProviderApiExecutionService(db).execute(
            http_request=http_request,
            ctx=ctx,
            provider_code=MINIMAX_PROVIDER_CODE,
            route_group="minimax_voice_clone",
            model_code=MINIMAX_DEFAULT_T2A_MODEL,
            provider_path=MINIMAX_GET_VOICE_PATH,
            payload={
                key: value
                for key, value in {
                    "voice_id": voice_id,
                    "q": q,
                    "page_index": page_index,
                    "page_size": page_size,
                }.items()
                if value is not None
            },
            forward_payload={
                key: value
                for key, value in {
                    "voice_id": voice_id,
                    "q": q,
                    "page_index": page_index,
                    "page_size": page_size,
                }.items()
                if value is not None
            },
            bill_on_success=False,
            persist_request_log=False,
        )
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=MINIMAX_PROVIDER_CODE,
        route_group="minimax_voice_clone",
        model_code=MINIMAX_DEFAULT_T2A_MODEL,
        provider_path=MINIMAX_GET_VOICE_PATH,
        payload={"voice_type": MINIMAX_CLONED_VOICE_TYPE},
        bill_on_success=False,
        persist_request_log=False,
    )
    return _build_minimax_voice_catalog_response(
        upstream_response,
        source_key="voice_cloning",
        voice_id=voice_id,
        q=q,
        page_index=page_index,
        page_size=page_size,
    )


@router.post(
    "/cloned-tts",
    summary="创建 MiniMax cloned voice 异步语音任务",
    response_model=MiniMaxT2AAsyncTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **COMMON_ESTIMATE_ERROR_RESPONSES},
)
async def create_minimax_cloned_tts(
    payload: MiniMaxClonedTtsRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """按能力型公开契约创建 MiniMax cloned voice 异步语音任务。"""
    await _validate_minimax_cloned_tts_request(payload)
    service = AsyncTaskExecutionService(db)
    return await service.create_task(
        http_request=http_request,
        ctx=ctx,
        route_group="minimax_t2a_async",
        fixed_model_code=payload.model,
        payload=_build_minimax_tts_payload(payload),
        forward_payload=payload.model_dump(exclude_none=True),
        chain=MINIMAX_PROVIDER_CODE,
        fallback=False,
        create_invoke_builder=_build_create_invoke_ctx,
        response_builder=_build_task_response_builder(
            voice_id=payload.voice_id,
            voice_type=MINIMAX_CLONED_VOICE_TYPE,
        ),
    )


@router.post(
    "/voice-clones",
    summary="创建 MiniMax 快速克隆音色",
    response_model=MiniMaxVoiceCloneResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def create_minimax_voice_clone(
    payload: MiniMaxVoiceCloneRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """创建 MiniMax 快速克隆音色。当前第一阶段只接受外部 `audio_url`。"""
    return await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=MINIMAX_PROVIDER_CODE,
        route_group="minimax_voice_clone",
        model_code=MINIMAX_DEFAULT_T2A_MODEL,
        provider_path=MINIMAX_VOICE_CLONE_PATH,
        payload=_build_minimax_voice_clone_payload(payload),
        forward_payload=payload.model_dump(exclude_none=True),
        bill_on_success=False,
    )


@router.delete(
    "/voice-clones/{voice_id}",
    summary="删除 MiniMax cloned voice",
    response_model=MiniMaxVoiceDeleteResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def delete_minimax_voice_clone(
    voice_id: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """删除指定的 MiniMax cloned voice。"""
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=MINIMAX_PROVIDER_CODE,
        route_group="minimax_voice_clone",
        model_code=MINIMAX_DEFAULT_T2A_MODEL,
        provider_path=MINIMAX_DELETE_VOICE_PATH,
        payload={"voice_id": voice_id},
        forward_payload={} if _using_35m_public_gateway() else None,
        bill_on_success=False,
    )
    if _using_35m_public_gateway():
        return upstream_response
    return _build_minimax_voice_delete_response(voice_id=voice_id)
