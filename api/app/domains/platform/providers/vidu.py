from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.vidu_video import build_vidu_request_payload
from app.domains.platform.providers.base import BaseProviderAdapter


def _normalize_task_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "success":
        return "completed"
    if normalized == "failed":
        return "failed"
    if normalized == "processing":
        return "processing"
    if normalized == "queueing":
        return "queued"
    return "submitted"


def _parse_created_at(value: Any) -> int | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(parsed.astimezone(timezone.utc).timestamp())


def _extract_first_creation(payload: dict[str, Any]) -> dict[str, Any]:
    creations = payload.get("creations")
    if not isinstance(creations, list) or not creations:
        return {}
    first = creations[0]
    return first if isinstance(first, dict) else {}


class ViduAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = dict(ctx.get("payload") or {})
        return build_vidu_request_payload(payload)

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        if not isinstance(resp, dict):
            return {"provider_raw": resp}

        path = str(ctx.get("path") or "")
        payload = dict(ctx.get("payload") or {})

        if path in {"/ent/v2/text2video", "/ent/v2/img2video", "/ent/v2/start-end2video"}:
            state = resp.get("state")
            created_at = _parse_created_at(resp.get("created_at")) or int(datetime.now(timezone.utc).timestamp())
            return {
                "id": str(resp.get("task_id") or resp.get("id") or ""),
                "object": "video",
                "status": _normalize_task_status(state),
                "provider_status": str(state).lower() if state is not None else "created",
                "model": payload.get("model"),
                "created_at": created_at,
                "credits": resp.get("credits"),
                "provider_raw": resp,
            }

        if path.endswith("/creations"):
            provider_model = ctx.get("provider_model")
            creation = _extract_first_creation(resp)
            state = resp.get("state")
            return {
                "id": str(resp.get("id") or getattr(provider_model, "provider_task_id", "") or ""),
                "object": "video",
                "status": _normalize_task_status(state),
                "provider_status": str(state).lower() if state is not None else None,
                "model": getattr(provider_model, "model_code", None),
                "created_at": _parse_created_at(resp.get("created_at")),
                "url": creation.get("url") or creation.get("watermarked_url"),
                "cover_url": creation.get("cover_url"),
                "watermarked_url": creation.get("watermarked_url"),
                "credits": resp.get("credits"),
                "bgm": resp.get("bgm"),
                "off_peak": resp.get("off_peak"),
                "creations": resp.get("creations"),
                "error": resp.get("err_code"),
                "video": creation or None,
                "provider_raw": resp,
            }

        return resp

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "vidu", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "vidu", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "vidu", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        video_url = result_payload.get("url")
        if not video_url:
            creation = _extract_first_creation(result_payload)
            video_url = creation.get("url") or creation.get("watermarked_url")
        if not video_url:
            raise httpx.HTTPError("vidu_video_not_ready")

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
            "Authorization": f"Token {provider.auth_config.get('api_key', '')}",
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
            return self.parse_response(ctx, response_payload)
