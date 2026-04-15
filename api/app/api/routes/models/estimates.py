from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import (
    AUTH_ERROR_RESPONSES,
    COMMON_ESTIMATE_ERROR_RESPONSES,
    MODEL_NOT_FOUND_RESPONSE,
    error_response,
)
from app.api.routes.models.kling_video import _validate_kling_video_request
from app.api.routes.models.minimax import _build_minimax_tts_payload
from app.api.routes.models.minimax_video import _validate_minimax_video_request
from app.api.routes.models.qwen import (
    _build_qwen_tts_payload,
    _build_qwen_voice_clone_create_payload,
    _validate_qwen_system_tts_request,
)
from app.api.routes.models.seedance import _validate_seedance_request
from app.api.routes.models.vidu import _validate_vidu_video_request
from app.api.routes.models.wan_video import _validate_wan_video_request
from app.api.schemas import (
    BananaRequest,
    EstimateRequest,
    EstimateSummaryResponse,
    GeminiGenerateContentRequest,
    KlingVideoRequest,
    MiniMaxSystemTtsRequest,
    MiniMaxT2AAsyncRequest,
    MiniMaxVideoRequest,
    OpenAIChatCompletionsRequest,
    OpenAIResponsesRequest,
    QwenClonedTtsRequest,
    QwenSystemTtsRequest,
    QwenVoiceCloneCreateRequest,
    SeedanceRequest,
    SeedreamLiteRequest,
    SeedreamRequest,
    ViduVideoRequest,
    VeoRequest,
    WanVideoRequest,
)
from app.core.provider_catalog.qwen_voices import (
    QWEN_SYSTEM_TTS_MODE_INSTRUCT,
    QWEN_SYSTEM_TTS_MODE_STANDARD,
    QWEN_TTS_CLONED_VOICE_MODEL,
    QWEN_TTS_SYSTEM_FLASH_MODEL,
    QWEN_TTS_SYSTEM_INSTRUCT_FLASH_MODEL,
)
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.proxy_execution import estimate_proxy_request

router = APIRouter(prefix="/v1")

_SYNC_ROUTE_GROUPS = frozenset(
    {
        "openai",
        "responses",
        "gemini",
        "banana",
        "seedream",
        "qwen_tts",
        "qwen_voice_clone",
    }
)
_ASYNC_ROUTE_GROUPS = frozenset(
    {
        "veo3",
        "veo31",
        "seedance",
        "wan_video",
        "kling_video",
        "minimax_video",
        "minimax_t2a_async",
        "vidu",
    }
)
_ESTIMATE_ROUTE_ERROR_RESPONSES = {
    422: error_response("请求体不符合公开模型契约，或当前模型暂不支持统一预计费接口。", "invalid_request_payload"),
}


def _http_422(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _validate_request_payload(model_cls, payload: dict[str, Any]):
    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise _http_422("invalid_request_payload") from exc


def _serialize_chain(chain: list[str] | None) -> str | None:
    if not chain:
        return None

    normalized: list[str] = []
    seen_provider_codes: set[str] = set()
    for raw_provider_code in chain:
        provider_code = str(raw_provider_code or "").strip()
        if not provider_code or provider_code in seen_provider_codes:
            continue
        seen_provider_codes.add(provider_code)
        normalized.append(provider_code)
    return ",".join(normalized) if normalized else None


def _resolve_public_route(model_code: str):
    route = get_platform_config_snapshot().get_primary_route(model_code, public_only=True)
    if route is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return route


def _quote_mode_for_route_group(route_group: str) -> str:
    if route_group in {"openai", "responses", "gemini"}:
        return "estimated"
    return "exact"


def _int_factor(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _decimal_price(price_fields: dict[str, Any], key: str) -> Decimal:
    return Decimal(str(price_fields.get(key) or "0"))


def _text_estimate_bounds_for_option(option: dict[str, Any]) -> tuple[Decimal, Decimal]:
    snapshot = dict(option.get("pricing_snapshot") or {})
    request_factors = dict(snapshot.get("request_factors") or {})
    user_price = dict(snapshot.get("user_price") or {})

    if not request_factors or not user_price:
        amount = Decimal(str(option.get("estimated_amount") or "0"))
        return amount, amount

    input_tokens = _int_factor(request_factors.get("input_tokens"))
    cached_input_tokens = _int_factor(request_factors.get("cached_input_tokens"))
    billable_input_tokens = max(
        0,
        _int_factor(request_factors.get("billable_input_tokens")) or input_tokens - cached_input_tokens,
    )
    output_tokens = _int_factor(request_factors.get("output_tokens"))
    pricing_tier = str(request_factors.get("pricing_tier") or "").strip()

    if "cache_miss_input_per_1m_tokens" in user_price or "cache_hit_input_per_1m_tokens" in user_price:
        cache_miss_input_price = _decimal_price(user_price, "cache_miss_input_per_1m_tokens")
        cache_hit_input_price = _decimal_price(user_price, "cache_hit_input_per_1m_tokens")
        output_price = _decimal_price(user_price, "output_per_1m_tokens")
        lower = (
            cache_miss_input_price * Decimal(billable_input_tokens)
            + cache_hit_input_price * Decimal(cached_input_tokens)
        ) / Decimal("1000000")
        upper = lower + (output_price * Decimal(output_tokens)) / Decimal("1000000")
        return lower, upper

    if pricing_tier and f"output_per_1m_tokens_{pricing_tier}" in user_price:
        input_price = _decimal_price(user_price, f"input_per_1m_tokens_{pricing_tier}")
        cached_input_price = _decimal_price(user_price, f"cached_input_per_1m_tokens_{pricing_tier}")
        output_price = _decimal_price(user_price, f"output_per_1m_tokens_{pricing_tier}")
        lower = (
            input_price * Decimal(billable_input_tokens)
            + cached_input_price * Decimal(cached_input_tokens)
        ) / Decimal("1000000")
        upper = lower + (output_price * Decimal(output_tokens)) / Decimal("1000000")
        return lower, upper

    if "cached_input_per_1m_tokens" in user_price:
        input_price = _decimal_price(user_price, "input_per_1m_tokens")
        cached_input_price = _decimal_price(user_price, "cached_input_per_1m_tokens")
        output_price = _decimal_price(user_price, "output_per_1m_tokens")
        lower = (
            input_price * Decimal(billable_input_tokens)
            + cached_input_price * Decimal(cached_input_tokens)
        ) / Decimal("1000000")
        upper = lower + (output_price * Decimal(output_tokens)) / Decimal("1000000")
        return lower, upper

    if "input_per_1m_tokens" in user_price and "output_per_1m_tokens" in user_price:
        input_price = _decimal_price(user_price, "input_per_1m_tokens")
        output_price = _decimal_price(user_price, "output_per_1m_tokens")
        lower = (input_price * Decimal(input_tokens)) / Decimal("1000000")
        upper = lower + (output_price * Decimal(output_tokens)) / Decimal("1000000")
        return lower, upper

    amount = Decimal(str(option.get("estimated_amount") or "0"))
    return amount, amount


def _to_public_estimate_summary(*, route_group: str, raw_response: dict[str, Any]) -> dict[str, Any]:
    provider_options = list(raw_response.get("provider_options") or [])
    selected_provider = dict(raw_response.get("selected_provider") or {})
    request_factors = dict(raw_response.get("request_factors") or {})
    account = dict(raw_response.get("account") or {})

    selected_amount = Decimal(str(selected_provider.get("estimated_amount") or "0"))
    quote_mode = _quote_mode_for_route_group(route_group)
    if quote_mode == "estimated":
        lower_values: list[Decimal] = []
        upper_values: list[Decimal] = []
        for item in provider_options or [selected_provider]:
            lower, upper = _text_estimate_bounds_for_option(item)
            lower_values.append(lower)
            upper_values.append(upper)
        lowest_amount = min(lower_values) if lower_values else selected_amount
        highest_amount = max(upper_values) if upper_values else selected_amount
    else:
        amount_values = [Decimal(str(item.get("estimated_amount") or "0")) for item in provider_options] or [selected_amount]
        lowest_amount = min(amount_values)
        highest_amount = max(amount_values)

    available_amount = Decimal(str(account.get("available_balance") or account.get("balance") or "0"))
    currency = str(selected_provider.get("currency") or "CNY")

    return {
        "model": str(raw_response.get("model") or ""),
        "quote_mode": quote_mode,
        "route_mode": str(raw_response.get("route_mode") or "default"),
        "lowest_price": str(lowest_amount),
        "highest_price": str(highest_amount),
        "currency": currency,
        "balance": {
            "available_amount": str(available_amount),
            "enough_for_highest": available_amount >= highest_amount,
        },
        "request_factors": request_factors,
    }


def _normalize_qwen_tts_payload(*, model_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    if model_code == QWEN_TTS_CLONED_VOICE_MODEL:
        validated_payload = _validate_request_payload(QwenClonedTtsRequest, payload)
        return _build_qwen_tts_payload(
            model=model_code,
            input_payload=validated_payload.model_dump(
                exclude_none=True,
                exclude={"instructions", "optimize_instructions"},
            ),
        )

    expected_mode_by_model = {
        QWEN_TTS_SYSTEM_FLASH_MODEL: QWEN_SYSTEM_TTS_MODE_STANDARD,
        QWEN_TTS_SYSTEM_INSTRUCT_FLASH_MODEL: QWEN_SYSTEM_TTS_MODE_INSTRUCT,
    }
    expected_mode = expected_mode_by_model.get(model_code)
    if expected_mode is None:
        raise _http_422("unsupported_qwen_tts_model")

    raw_mode = payload.get("mode")
    if raw_mode is not None and str(raw_mode).strip().lower() != expected_mode:
        raise _http_422("mode_model_mismatch")

    normalized_payload = {**payload, "mode": expected_mode}
    validated_payload = _validate_request_payload(QwenSystemTtsRequest, normalized_payload)
    _validate_qwen_system_tts_request(validated_payload)
    return _build_qwen_tts_payload(
        model=model_code,
        input_payload=validated_payload.model_dump(exclude_none=True, exclude={"mode"}),
    )


def _normalize_minimax_t2a_payload(*, model_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        validated_payload = MiniMaxT2AAsyncRequest.model_validate({**payload, "model": model_code})
    except ValidationError:
        validated_payload = _validate_request_payload(MiniMaxSystemTtsRequest, {**payload, "model": model_code})
        return _build_minimax_tts_payload(validated_payload)
    return validated_payload.model_dump(exclude_none=True)


def _normalize_payload_for_estimate(*, route_group: str, model_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    if route_group == "openai":
        validated_payload = _validate_request_payload(
            OpenAIChatCompletionsRequest,
            {**payload, "model": model_code},
        )
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "responses":
        validated_payload = _validate_request_payload(
            OpenAIResponsesRequest,
            {**payload, "model": model_code},
        )
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "gemini":
        validated_payload = _validate_request_payload(GeminiGenerateContentRequest, payload)
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "banana":
        validated_payload = _validate_request_payload(BananaRequest, payload)
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "seedream":
        request_model = SeedreamLiteRequest if model_code == "doubao-seedream-5.0-lite" else SeedreamRequest
        validated_payload = _validate_request_payload(request_model, payload)
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "seedance":
        validated_payload = _validate_request_payload(SeedanceRequest, payload)
        payload_data = validated_payload.model_dump(exclude_none=True)
        _validate_seedance_request(payload=payload_data)
        return payload_data

    if route_group in {"veo3", "veo31"}:
        validated_payload = _validate_request_payload(VeoRequest, payload)
        return validated_payload.model_dump(exclude_none=True)

    if route_group == "wan_video":
        validated_payload = _validate_request_payload(WanVideoRequest, payload)
        payload_data = validated_payload.model_dump(exclude_none=True)
        _validate_wan_video_request(model_code=model_code, payload=payload_data)
        return payload_data

    if route_group == "kling_video":
        validated_payload = _validate_request_payload(KlingVideoRequest, payload)
        payload_data = validated_payload.model_dump(exclude_none=True)
        _validate_kling_video_request(payload_data)
        return payload_data

    if route_group == "minimax_video":
        validated_payload = _validate_request_payload(MiniMaxVideoRequest, payload)
        payload_data = validated_payload.model_dump(exclude_none=True)
        _validate_minimax_video_request(model_code=model_code, payload=payload_data)
        return payload_data

    if route_group == "vidu":
        validated_payload = _validate_request_payload(ViduVideoRequest, payload)
        payload_data = validated_payload.model_dump(exclude_none=True)
        _validate_vidu_video_request(model_code=model_code, payload=payload_data)
        return payload_data

    if route_group == "qwen_tts":
        return _normalize_qwen_tts_payload(model_code=model_code, payload=payload)

    if route_group == "qwen_voice_clone":
        validated_payload = _validate_request_payload(QwenVoiceCloneCreateRequest, payload)
        return _build_qwen_voice_clone_create_payload(
            payload=validated_payload,
            audio_source=validated_payload.audio_url,
        )

    if route_group == "minimax_t2a_async":
        return _normalize_minimax_t2a_payload(model_code=model_code, payload=payload)

    raise _http_422("estimate_route_not_supported")


@router.post(
    "/estimates",
    summary="统一预计费测算接口",
    response_model=EstimateSummaryResponse,
    responses={
        **AUTH_ERROR_RESPONSES,
        **COMMON_ESTIMATE_ERROR_RESPONSES,
        **MODEL_NOT_FOUND_RESPONSE,
        **_ESTIMATE_ROUTE_ERROR_RESPONSES,
    },
)
async def create_estimate(
    payload: EstimateRequest,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = _resolve_public_route(payload.model)
    normalized_payload = _normalize_payload_for_estimate(
        route_group=route.route_group,
        model_code=payload.model,
        payload=payload.payload,
    )
    chain = _serialize_chain(payload.chain)

    if route.route_group in _SYNC_ROUTE_GROUPS:
        allow_fallback = True if payload.fallback is None else payload.fallback
        raw_response = estimate_proxy_request(
            ctx=ctx,
            db=db,
            route_group=route.route_group,
            requested_model=payload.model,
            payload=normalized_payload,
            chain=chain,
            allow_fallback=allow_fallback,
            metrics_window=payload.metrics_window,
        )
        return _to_public_estimate_summary(route_group=route.route_group, raw_response=raw_response)

    if route.route_group in _ASYNC_ROUTE_GROUPS:
        raw_response = AsyncTaskExecutionService(db).estimate_task(
            ctx=ctx,
            route_group=route.route_group,
            fixed_model_code=payload.model,
            payload=normalized_payload,
            chain=chain,
            fallback=payload.fallback,
            metrics_window=payload.metrics_window,
        )
        return _to_public_estimate_summary(route_group=route.route_group, raw_response=raw_response)

    raise _http_422("estimate_route_not_supported")
