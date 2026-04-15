from __future__ import annotations

import asyncio
import httpx
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, UserAccessContext, require_api_key, require_user_access
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, PROVIDER_API_ERROR_RESPONSES
from app.api.schemas import (
    QwenClonedTtsRequest,
    QwenSystemTtsRequest,
    QwenSystemVoiceListResponse,
    QwenTtsResponse,
    QwenVoiceCloneCreateRequest,
    QwenVoiceCloneResponse,
    QwenVoiceDeleteResponse,
    QwenVoiceListResponse,
)
from app.core.provider_catalog import get_provider
from app.core.provider_catalog.qwen_voices import (
    QWEN_SYSTEM_TTS_MODE_INSTRUCT,
    QWEN_SYSTEM_TTS_MODE_TO_MODEL,
    QWEN_SYSTEM_TTS_MODES,
    QWEN_SYSTEM_VOICES,
    QWEN_TTS_CLONED_VOICE_MODEL,
    qwen_published_system_voice_mode_map,
    qwen_system_voice_modes,
    qwen_system_voice_names,
)
from app.domains.platform.providers.registry import get_adapter
from app.domains.platform.services.provider_api_execution import ProviderApiExecutionService

router = APIRouter(prefix="/v1/qwen")

QWEN_PROVIDER_CODE = "35m"
QWEN_VOICE_CLONE_MODEL = "qwen-voice-enrollment"
QWEN_TTS_PATH = "/api/v1/services/aigc/multimodal-generation/generation"
QWEN_VOICE_CLONE_PATH = "/api/v1/services/audio/tts/customization"
QWEN_CLONED_VOICE_VALIDATION_PAGE_SIZE = 100
QWEN_CLONED_VOICE_VALIDATION_MAX_PAGES = 10
QWEN_SYSTEM_VOICE_NAMES = qwen_system_voice_names()
QWEN_PUBLISHED_SYSTEM_VOICE_MODES = qwen_published_system_voice_mode_map()


def _using_35m_public_gateway() -> bool:
    return QWEN_PROVIDER_CODE == "35m"


def _build_qwen_tts_payload(*, model: str, input_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "input": {key: value for key, value in input_payload.items() if value is not None},
    }


def _build_qwen_voice_clone_create_payload(
    *,
    payload: QwenVoiceCloneCreateRequest,
    audio_source: str,
) -> dict[str, Any]:
    input_payload: dict[str, Any] = {
        "action": "create",
        "target_model": QWEN_TTS_CLONED_VOICE_MODEL,
        "preferred_name": payload.name,
        "audio": {
            "data": audio_source,
        },
    }
    if payload.text:
        input_payload["text"] = payload.text
    if payload.language:
        input_payload["language"] = payload.language
    return {
        "model": QWEN_VOICE_CLONE_MODEL,
        "input": input_payload,
    }


def _build_qwen_voice_clone_list_payload(*, page_index: int, page_size: int) -> dict[str, Any]:
    return {
        "model": QWEN_VOICE_CLONE_MODEL,
        "input": {
            "action": "list",
            "page_index": page_index,
            "page_size": page_size,
        },
    }


async def _list_qwen_voice_clones_raw(
    *,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    page_index: int,
    page_size: int,
) -> dict[str, Any]:
    return await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=QWEN_PROVIDER_CODE,
        route_group="qwen_voice_clone",
        model_code=QWEN_VOICE_CLONE_MODEL,
        provider_path=QWEN_VOICE_CLONE_PATH,
        payload=_build_qwen_voice_clone_list_payload(page_index=page_index, page_size=page_size),
        bill_on_success=False,
        persist_request_log=False,
    )


def _build_qwen_system_voice_item(voice_item: dict[str, Any]) -> dict[str, Any]:
    modes = qwen_system_voice_modes(voice_item)
    return {
        "voice": str(voice_item.get("voice") or ""),
        "locale": voice_item.get("locale"),
        "languages": [
            language
            for language in voice_item.get("languages", [])
            if isinstance(language, str) and language
        ],
        "description": voice_item.get("description"),
        "modes": modes,
    }


def _build_qwen_system_voice_list_response(
    *,
    language: str | None,
    locale: str | None,
    mode: str | None,
    voice: str | None,
    q: str | None,
    page_index: int,
    page_size: int,
) -> dict[str, Any]:
    normalized_language = (language or "").strip().lower()
    normalized_locale = (locale or "").strip().lower()
    normalized_mode = (mode or "").strip().lower()
    normalized_voice = (voice or "").strip().lower()
    normalized_q = (q or "").strip().lower()

    if normalized_mode and normalized_mode not in QWEN_SYSTEM_TTS_MODES:
        raise HTTPException(status_code=422, detail="invalid_mode")

    items: list[dict[str, Any]] = []
    for raw_voice_item in QWEN_SYSTEM_VOICES:
        item = _build_qwen_system_voice_item(dict(raw_voice_item))
        if not item["modes"]:
            continue
        if normalized_language and normalized_language not in {
            str(value).strip().lower() for value in item["languages"]
        }:
            continue
        if normalized_locale and str(item.get("locale") or "").strip().lower() != normalized_locale:
            continue
        if normalized_mode and normalized_mode not in item["modes"]:
            continue
        if normalized_voice and str(item.get("voice") or "").strip().lower() != normalized_voice:
            continue
        if normalized_q:
            searchable = " ".join(
                [
                    str(item.get("voice") or ""),
                    str(item.get("description") or ""),
                    str(item.get("locale") or ""),
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


def _build_qwen_tts_response(
    upstream_response: dict[str, Any],
    *,
    voice: str,
    mode: str | None = None,
) -> dict[str, Any]:
    response = {
        "request_id": upstream_response.get("request_id") if isinstance(upstream_response, dict) else None,
        "voice": voice,
        "output": upstream_response.get("output") if isinstance(upstream_response, dict) else None,
        "usage": upstream_response.get("usage") if isinstance(upstream_response, dict) else None,
    }
    if mode is not None:
        response["mode"] = mode
    return response


def _build_qwen_voice_clone_create_response(
    upstream_response: dict[str, Any],
    *,
    name: str,
) -> dict[str, Any]:
    output = upstream_response.get("output") if isinstance(upstream_response, dict) else None
    return {
        "request_id": upstream_response.get("request_id") if isinstance(upstream_response, dict) else None,
        "voice": output.get("voice") if isinstance(output, dict) else None,
        "name": name,
        "usage": upstream_response.get("usage") if isinstance(upstream_response, dict) else None,
    }


def _build_qwen_voice_clone_list_response(
    upstream_response: dict[str, Any],
    *,
    page_index: int,
    page_size: int,
) -> dict[str, Any]:
    output = upstream_response.get("output") if isinstance(upstream_response, dict) else None
    voice_list = output.get("voice_list") if isinstance(output, dict) else None
    items = [
        {
            "voice": item.get("voice"),
            "gmt_create": item.get("gmt_create"),
        }
        for item in voice_list
        if isinstance(item, dict)
    ] if isinstance(voice_list, list) else []
    return {
        "request_id": upstream_response.get("request_id") if isinstance(upstream_response, dict) else None,
        "items": items,
        "page_index": page_index,
        "page_size": page_size,
        "usage": upstream_response.get("usage") if isinstance(upstream_response, dict) else None,
    }


def _build_qwen_voice_delete_response(
    upstream_response: dict[str, Any],
    *,
    voice: str,
) -> dict[str, Any]:
    return {
        "request_id": upstream_response.get("request_id") if isinstance(upstream_response, dict) else None,
        "voice": voice,
        "deleted": True,
    }


async def _fetch_qwen_cloned_voice_names_for_validation() -> set[str]:
    provider = get_provider(QWEN_PROVIDER_CODE)
    adapter = get_adapter(provider.adapter_key)
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            collected: set[str] = set()
            for page_index in range(QWEN_CLONED_VOICE_VALIDATION_MAX_PAGES):
                result = await adapter.invoke(
                    {
                        "provider": provider,
                        "path": QWEN_VOICE_CLONE_PATH,
                        "payload": _build_qwen_voice_clone_list_payload(
                            page_index=page_index,
                            page_size=QWEN_CLONED_VOICE_VALIDATION_PAGE_SIZE,
                        ),
                        "method": "POST",
                    }
                )
                output = result.get("output") if isinstance(result, dict) else None
                voice_list = output.get("voice_list") if isinstance(output, dict) else None
                if not isinstance(voice_list, list):
                    break
                collected.update(
                    voice
                    for item in voice_list
                    if isinstance(item, dict)
                    for voice in [item.get("voice")]
                    if isinstance(voice, str) and voice
                )
                if len(voice_list) < QWEN_CLONED_VOICE_VALIDATION_PAGE_SIZE:
                    break
            if collected:
                return collected
        except (httpx.HTTPError, KeyError) as exc:
            last_exc = exc
        if attempt < 2:
            await asyncio.sleep(1)

    raise HTTPException(status_code=502, detail="cloned_voice_lookup_failed") from last_exc


def _validate_qwen_system_tts_request(payload: QwenSystemTtsRequest) -> None:
    if payload.mode not in QWEN_SYSTEM_TTS_MODES:
        raise HTTPException(status_code=422, detail="invalid_mode")
    published_modes = QWEN_PUBLISHED_SYSTEM_VOICE_MODES.get(payload.voice)
    if not published_modes or payload.mode not in published_modes:
        raise HTTPException(status_code=422, detail="system_voice_required")
    if payload.mode != QWEN_SYSTEM_TTS_MODE_INSTRUCT and (
        payload.instructions is not None or payload.optimize_instructions is not None
    ):
        raise HTTPException(status_code=422, detail="instructions_not_allowed")


async def _validate_qwen_cloned_tts_request(payload: QwenClonedTtsRequest) -> None:
    if payload.instructions is not None or payload.optimize_instructions is not None:
        raise HTTPException(status_code=422, detail="instructions_not_allowed")
    if payload.voice in QWEN_SYSTEM_VOICE_NAMES:
        raise HTTPException(status_code=422, detail="cloned_voice_required")
    if _using_35m_public_gateway():
        return

    cloned_voice_names = await _fetch_qwen_cloned_voice_names_for_validation()
    if payload.voice not in cloned_voice_names:
        raise HTTPException(status_code=422, detail="cloned_voice_required")


@router.get(
    "/system-voices",
    summary="获取 Qwen system voice 列表",
    response_model=QwenSystemVoiceListResponse,
    responses=AUTH_ERROR_RESPONSES,
)
async def list_qwen_system_voices(
    ctx: UserAccessContext = Depends(require_user_access),
    language: str | None = Query(default=None, description="按语种筛选，例如 `zh`、`en`。"),
    locale: str | None = Query(default=None, description="按 locale 精确筛选，例如 `zh-CN`、`zh-CN-yue`。"),
    mode: str | None = Query(default=None, description="按 system TTS 模式筛选，支持 `standard`、`instruct`。"),
    voice: str | None = Query(default=None, description="按 voice 精确筛选。"),
    q: str | None = Query(default=None, description="按 voice、描述或 locale 进行模糊搜索。"),
    page_index: int = Query(default=0, ge=0, le=1000000, description="页码索引。"),
    page_size: int = Query(default=20, ge=1, le=1000000, description="每页返回条数。"),
) -> dict[str, Any]:
    """返回平台整理后的 Qwen system voice 目录。"""
    del ctx
    return _build_qwen_system_voice_list_response(
        language=language,
        locale=locale,
        mode=mode,
        voice=voice,
        q=q,
        page_index=page_index,
        page_size=page_size,
    )


@router.post(
    "/system-tts",
    summary="创建 Qwen system voice 语音合成",
    response_model=QwenTtsResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def create_qwen_system_tts(
    payload: QwenSystemTtsRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """按能力型公开契约创建 Qwen system voice 非流式语音合成。"""
    _validate_qwen_system_tts_request(payload)
    public_payload = payload.model_dump(exclude_none=True)
    model_code = QWEN_SYSTEM_TTS_MODE_TO_MODEL[payload.mode]
    provider_payload = _build_qwen_tts_payload(
        model=model_code,
        input_payload=payload.model_dump(exclude_none=True, exclude={"mode"}),
    )
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=QWEN_PROVIDER_CODE,
        route_group="qwen_tts",
        model_code=model_code,
        provider_path=QWEN_TTS_PATH,
        payload=provider_payload,
        forward_payload=public_payload,
        bill_on_success=True,
    )
    if _using_35m_public_gateway():
        return upstream_response
    return _build_qwen_tts_response(upstream_response, voice=payload.voice, mode=payload.mode)


@router.post(
    "/cloned-tts",
    summary="创建 Qwen cloned voice 语音合成",
    response_model=QwenTtsResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def create_qwen_cloned_tts(
    payload: QwenClonedTtsRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """按能力型公开契约创建 Qwen cloned voice 非流式语音合成。"""
    await _validate_qwen_cloned_tts_request(payload)
    public_payload = payload.model_dump(exclude_none=True)
    provider_payload = _build_qwen_tts_payload(
        model=QWEN_TTS_CLONED_VOICE_MODEL,
        input_payload=payload.model_dump(exclude_none=True, exclude={"instructions", "optimize_instructions"}),
    )
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=QWEN_PROVIDER_CODE,
        route_group="qwen_tts",
        model_code=QWEN_TTS_CLONED_VOICE_MODEL,
        provider_path=QWEN_TTS_PATH,
        payload=provider_payload,
        forward_payload=public_payload,
        bill_on_success=True,
    )
    if _using_35m_public_gateway():
        return upstream_response
    return _build_qwen_tts_response(upstream_response, voice=payload.voice)


@router.post(
    "/voice-clones",
    summary="创建 Qwen cloned voice",
    response_model=QwenVoiceCloneResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def create_qwen_voice_clone(
    payload: QwenVoiceCloneCreateRequest,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """创建 Qwen cloned voice。当前第一阶段只接受外部 `audio_url`。"""
    public_payload = payload.model_dump(exclude_none=True)
    provider_payload = _build_qwen_voice_clone_create_payload(
        payload=payload,
        audio_source=payload.audio_url,
    )
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=QWEN_PROVIDER_CODE,
        route_group="qwen_voice_clone",
        model_code=QWEN_VOICE_CLONE_MODEL,
        provider_path=QWEN_VOICE_CLONE_PATH,
        payload=provider_payload,
        forward_payload=public_payload,
        bill_on_success=True,
    )
    if _using_35m_public_gateway():
        return upstream_response
    return _build_qwen_voice_clone_create_response(upstream_response, name=payload.name)


@router.get(
    "/voice-clones",
    summary="获取 Qwen cloned voice 列表",
    response_model=QwenVoiceListResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def list_qwen_voice_clones(
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
    page_index: int = Query(default=0, ge=0, le=1000000, description="页码索引。"),
    page_size: int = Query(default=10, ge=1, le=1000000, description="每页返回条数。"),
) -> dict[str, Any]:
    """读取当前 Qwen 账号下的 cloned voice 列表。"""
    if _using_35m_public_gateway():
        return await ProviderApiExecutionService(db).execute(
            http_request=http_request,
            ctx=ctx,
            provider_code=QWEN_PROVIDER_CODE,
            route_group="qwen_voice_clone",
            model_code=QWEN_VOICE_CLONE_MODEL,
            provider_path=QWEN_VOICE_CLONE_PATH,
            payload={
                "page_index": page_index,
                "page_size": page_size,
            },
            forward_payload={
                "page_index": page_index,
                "page_size": page_size,
            },
            bill_on_success=False,
            persist_request_log=False,
        )
    upstream_response = await _list_qwen_voice_clones_raw(
        http_request=http_request,
        ctx=ctx,
        db=db,
        page_index=page_index,
        page_size=page_size,
    )
    return _build_qwen_voice_clone_list_response(
        upstream_response,
        page_index=page_index,
        page_size=page_size,
    )


@router.delete(
    "/voice-clones/{voice}",
    summary="删除 Qwen cloned voice",
    response_model=QwenVoiceDeleteResponse,
    responses={**AUTH_ERROR_RESPONSES, **PROVIDER_API_ERROR_RESPONSES},
)
async def delete_qwen_voice_clone(
    voice: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """删除指定 Qwen cloned voice。"""
    payload_body = {
        "model": QWEN_VOICE_CLONE_MODEL,
        "input": {
            "action": "delete",
            "voice": voice,
        },
    }
    upstream_response = await ProviderApiExecutionService(db).execute(
        http_request=http_request,
        ctx=ctx,
        provider_code=QWEN_PROVIDER_CODE,
        route_group="qwen_voice_clone",
        model_code=QWEN_VOICE_CLONE_MODEL,
        provider_path=QWEN_VOICE_CLONE_PATH,
        payload=payload_body,
        forward_payload={} if _using_35m_public_gateway() else None,
        bill_on_success=False,
    )
    if _using_35m_public_gateway():
        return upstream_response
    return _build_qwen_voice_delete_response(upstream_response, voice=voice)
