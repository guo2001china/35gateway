from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.kling_video import (
    detect_kling_video_input_mode,
    normalize_kling_reference_images,
    resolve_kling_upstream_model,
    resolve_kling_video_duration,
    resolve_kling_video_mode,
)
from app.domains.platform.providers.base import BaseProviderAdapter


def _normalize_task_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"succeed", "succeeded", "completed", "success"}:
        return "completed"
    if normalized in {"failed", "error"}:
        return "failed"
    if normalized == "processing":
        return "processing"
    return "submitted"


def _created_at_seconds(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed // 1000 if parsed > 10_000_000_000 else parsed


def _raise_for_kling_error(payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    code = payload.get("code")
    if code in {None, 0, "0"}:
        return
    message = str(payload.get("message") or "kling_api_error")
    detail = f"kling_api_error:{code}:{message}"
    normalized_message = message.lower()
    if "auth" in normalized_message or "token" in normalized_message or "unauthorized" in normalized_message:
        raise HTTPException(status_code=401, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


def _extract_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _extract_video_item(payload: dict[str, Any]) -> dict[str, Any]:
    data = _extract_data(payload)
    task_result = data.get("task_result")
    if not isinstance(task_result, dict):
        return {}
    videos = task_result.get("videos")
    if not isinstance(videos, list) or not videos:
        return {}
    first = videos[0]
    return first if isinstance(first, dict) else {}


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _build_kling_jwt(access_key: str, secret_key: str, *, ttl_seconds: int = 1800) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": now + ttl_seconds,
        "nbf": now - 5,
    }
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def _build_authorization_header(auth_config: dict[str, Any]) -> str:
    api_key = str(auth_config.get("api_key") or "").strip()
    if api_key:
        return f"Bearer {api_key}"

    access_key = str(auth_config.get("access_key") or "").strip()
    secret_key = str(auth_config.get("secret_key") or "").strip()
    if access_key and secret_key:
        return f"Bearer {_build_kling_jwt(access_key, secret_key)}"

    raise HTTPException(status_code=503, detail="kling_credentials_not_configured")


class KlingAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = dict(ctx.get("payload") or {})
        public_model_code = str(payload.get("model") or "")
        upstream_model_code = resolve_kling_upstream_model(public_model_code)
        if upstream_model_code is None:
            raise HTTPException(status_code=422, detail="unsupported_model")

        input_mode = detect_kling_video_input_mode(payload)
        request_payload: dict[str, Any] = {
            "model_name": upstream_model_code,
            "prompt": payload.get("prompt"),
            "duration": str(resolve_kling_video_duration(payload)),
            "mode": resolve_kling_video_mode(payload),
            "sound": "off",
        }

        aspect_ratio = payload.get("aspect_ratio")
        if aspect_ratio is not None:
            request_payload["aspect_ratio"] = aspect_ratio

        if payload.get("watermark") is not None:
            request_payload["watermark_info"] = {"enabled": bool(payload.get("watermark"))}

        callback_url = payload.get("callback_url")
        if callback_url is not None:
            request_payload["callback_url"] = callback_url

        external_task_id = payload.get("external_task_id")
        if external_task_id is not None:
            request_payload["external_task_id"] = external_task_id

        if input_mode == "image":
            first_frame = payload.get("first_frame")
            if first_frame is not None:
                request_payload["image_list"] = [{"image_url": first_frame, "type": "first_frame"}]
            else:
                request_payload["image_list"] = [{"image_url": payload.get("input_reference")}]
        elif input_mode == "first_last_frame":
            request_payload["image_list"] = [
                {"image_url": payload.get("first_frame"), "type": "first_frame"},
                {"image_url": payload.get("last_frame"), "type": "end_frame"},
            ]
        elif input_mode == "reference_images":
            request_payload["image_list"] = [
                {"image_url": image_url} for image_url in normalize_kling_reference_images(payload)
            ]
        elif input_mode == "video_reference":
            request_payload["video_list"] = [
                {
                    "video_url": payload.get("video_url"),
                    "refer_type": "feature",
                    "keep_original_sound": "no",
                }
            ]

        return request_payload

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        if not isinstance(resp, dict):
            return {"provider_raw": resp}

        path = str(ctx.get("path") or "")
        payload = dict(ctx.get("payload") or {})
        public_model_code = str(payload.get("model") or "")
        data = _extract_data(resp)
        video_item = _extract_video_item(resp)

        if path == "/v1/videos/omni-video":
            task_id = data.get("task_id")
            task_status = data.get("task_status")
            created_at = _created_at_seconds(data.get("created_at")) or int(datetime.now(timezone.utc).timestamp())
            return {
                "id": str(task_id) if task_id is not None else None,
                "object": "video",
                "status": _normalize_task_status(task_status),
                "provider_status": str(task_status).lower() if task_status is not None else "submitted",
                "model": public_model_code or None,
                "resolved_model": resolve_kling_upstream_model(public_model_code),
                "created_at": created_at,
                "seconds": str(resolve_kling_video_duration(payload)),
                "provider_raw": resp,
            }

        if path.startswith("/v1/videos/omni-video/"):
            provider_model = ctx.get("provider_model")
            cached_result = getattr(provider_model, "result_payload", None) or {}
            task_id = data.get("task_id")
            task_status = data.get("task_status")
            task_status_msg = data.get("task_status_msg")
            return {
                "id": str(task_id) if task_id is not None else None,
                "object": "video",
                "status": _normalize_task_status(task_status),
                "provider_status": str(task_status).lower() if task_status is not None else None,
                "model": getattr(provider_model, "model_code", None),
                "resolved_model": cached_result.get("resolved_model") or "kling-video-o1",
                "created_at": _created_at_seconds(data.get("created_at")),
                "seconds": str(video_item.get("duration")) if video_item.get("duration") is not None else None,
                "url": video_item.get("url") or video_item.get("watermark_url"),
                "video": video_item or None,
                "error": task_status_msg if task_status_msg else None,
                "provider_raw": resp,
            }

        return resp

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "kling", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "kling", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "kling", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        video_url = result_payload.get("url")
        if not video_url and isinstance(result_payload.get("video"), dict):
            video_url = result_payload["video"].get("url") or result_payload["video"].get("watermark_url")
        if not video_url:
            raise httpx.HTTPError("kling_video_not_ready")

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
            "Authorization": _build_authorization_header(provider.auth_config),
        }
        if method != "GET":
            headers["Content-Type"] = "application/json"

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
            _raise_for_kling_error(response_payload)
            return self.parse_response(ctx, response_payload)
