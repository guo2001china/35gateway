from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.wan_video import (
    detect_wan_video_input_mode,
    normalize_wan_reference_urls,
    resolve_wan_video_size,
    resolve_wan_video_upstream_model,
)
from app.domains.platform.providers.base import BaseProviderAdapter


def _wan_task_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"succeeded", "success", "completed"}:
        return "completed"
    if normalized in {"failed", "canceled", "cancelled"}:
        return "failed"
    if normalized in {"running", "processing"}:
        return "processing"
    return "submitted"


def _raise_for_dashscope_error(payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    code = payload.get("code")
    if not code:
        return
    message = str(payload.get("message") or payload.get("msg") or "dashscope_api_error")
    detail = f"dashscope_api_error:{code}:{message}"
    normalized = str(code).lower()
    if "apikey" in normalized or "token" in normalized:
        raise HTTPException(status_code=401, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


def _extract_output(payload: dict[str, Any]) -> dict[str, Any]:
    output = payload.get("output")
    return output if isinstance(output, dict) else {}


def _extract_video_url(payload: dict[str, Any]) -> str | None:
    output = _extract_output(payload)
    for key in ("video_url", "url"):
        value = output.get(key)
        if isinstance(value, str) and value:
            return value

    for key in ("video_urls", "results", "videos"):
        value = output.get(key)
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str) and first:
                return first
            if isinstance(first, dict):
                for nested_key in ("url", "video_url"):
                    nested_value = first.get(nested_key)
                    if isinstance(nested_value, str) and nested_value:
                        return nested_value
    return None


class WanAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = dict(ctx.get("payload") or {})
        public_model_code = str(payload.get("model") or "")
        upstream_model_code = resolve_wan_video_upstream_model(public_model_code, payload)
        if upstream_model_code is None:
            raise HTTPException(status_code=422, detail="unsupported_input_mode_for_model")

        size = resolve_wan_video_size(payload)
        if size is None:
            raise HTTPException(status_code=422, detail="invalid_size_or_resolution")

        request_payload: dict[str, Any] = {
            "model": upstream_model_code,
            "input": {},
            "parameters": {
                "size": size,
            },
        }

        prompt = payload.get("prompt")
        if prompt is not None:
            request_payload["input"]["prompt"] = prompt

        if payload.get("audio_url") is not None:
            request_payload["input"]["audio_url"] = payload["audio_url"]
        if payload.get("negative_prompt") is not None:
            request_payload["input"]["negative_prompt"] = payload["negative_prompt"]

        input_mode = detect_wan_video_input_mode(payload)
        if input_mode == "image":
            request_payload["input"]["img_url"] = payload.get("input_reference")
        elif input_mode == "reference":
            request_payload["input"]["reference_urls"] = normalize_wan_reference_urls(payload)

        seconds = payload.get("seconds", payload.get("duration"))
        if seconds is not None:
            request_payload["parameters"]["duration"] = int(seconds)

        optional_parameters = {
            "prompt_extend": payload.get("prompt_extend"),
            "audio": payload.get("generate_audio"),
            "watermark": payload.get("watermark"),
            "seed": payload.get("seed"),
        }
        if input_mode == "reference" and payload.get("shot_type") is not None:
            optional_parameters["shot_type"] = payload["shot_type"]

        for key, value in optional_parameters.items():
            if value is not None:
                request_payload["parameters"][key] = value

        return request_payload

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        if not isinstance(resp, dict):
            return {"provider_raw": resp}

        path = str(ctx.get("path") or "")
        payload = dict(ctx.get("payload") or {})
        public_model_code = str(payload.get("model") or "")
        output = _extract_output(resp)
        resolved_model = resolve_wan_video_upstream_model(public_model_code, payload) if payload else None

        if path == "/api/v1/services/aigc/video-generation/video-synthesis":
            task_id = output.get("task_id")
            return {
                "id": str(task_id) if task_id is not None else None,
                "object": "video",
                "status": "submitted",
                "provider_status": "submitted",
                "model": public_model_code or None,
                "resolved_model": resolved_model,
                "created_at": int(datetime.now(timezone.utc).timestamp()),
                "seconds": str(payload.get("seconds") or payload.get("duration")) if payload.get("seconds") or payload.get("duration") else None,
                "size": resolve_wan_video_size(payload),
                "provider_raw": resp,
            }

        if path.startswith("/api/v1/tasks/"):
            provider_model = ctx.get("provider_model")
            cached_result = getattr(provider_model, "result_payload", None) or {}
            task_id = output.get("task_id") or resp.get("task_id")
            task_status = output.get("task_status") or output.get("status") or resp.get("status")
            video_url = _extract_video_url(resp)
            usage = resp.get("usage") if isinstance(resp.get("usage"), dict) else {}
            return {
                "id": str(task_id) if task_id is not None else None,
                "object": "video",
                "status": _wan_task_status(task_status),
                "provider_status": str(task_status).lower() if task_status is not None else None,
                "model": getattr(provider_model, "model_code", None),
                "resolved_model": cached_result.get("resolved_model"),
                "seconds": str(usage.get("duration")) if usage.get("duration") is not None else None,
                "size": usage.get("video_ratio") or usage.get("size"),
                "url": video_url,
                "provider_raw": resp,
            }

        return resp

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "wan", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "wan", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "wan", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        video_url = result_payload.get("url") or _extract_video_url(result_payload)
        if not video_url:
            raise httpx.HTTPError("wan_video_not_ready")

        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content, response.headers.get("content-type")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        path = str(ctx.get("path") or "")
        method = str(ctx.get("method", "POST")).upper()
        timeout = httpx.Timeout(180.0)

        headers = {
            "Authorization": f"Bearer {provider.auth_config.get('api_key', '')}",
        }
        if method != "GET":
            headers.update(
                {
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                }
            )

        request_payload: dict[str, Any] | None = None
        if method != "GET":
            request_payload = self.build_request(ctx)

        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout, follow_redirects=True) as client:
            if method == "GET":
                response = await client.get(path, headers=headers)
            else:
                response = await client.post(path, json=request_payload, headers=headers)
            response.raise_for_status()
            if not response.content:
                return {}
            response_payload = response.json()
            _raise_for_dashscope_error(response_payload)
            return self.parse_response(ctx, response_payload)
