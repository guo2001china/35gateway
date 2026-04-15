from __future__ import annotations

import io
import mimetypes
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException

from app.core.provider_support import detect_minimax_video_input_mode
from app.domains.platform.providers.base import BaseProviderAdapter


def _minimax_task_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"success", "completed"}:
        return "completed"
    if normalized in {"failed", "expired", "fail"}:
        return "failed"
    if normalized in {"processing", "rendering"}:
        return "processing"
    return "submitted"


def _raise_for_base_resp(payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    base_resp = payload.get("base_resp")
    if not isinstance(base_resp, dict):
        return
    raw_code = base_resp.get("status_code")
    if raw_code in (None, 0, "0"):
        return
    try:
        status_code = int(raw_code)
    except (TypeError, ValueError):
        status_code = None
    status_msg = str(base_resp.get("status_msg") or "minimax_api_error")
    detail = f"minimax_api_error:{status_code or raw_code}:{status_msg}"
    if status_code == 2049:
        raise HTTPException(status_code=401, detail=detail)
    if status_code == 1008:
        raise HTTPException(status_code=402, detail=detail)
    if status_code in {1002, 1041, 2045, 2056}:
        raise HTTPException(status_code=429, detail=detail)
    if status_code in {2039}:
        raise HTTPException(status_code=409, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


def _unwrap_single_file_tar(content: bytes, content_type: str | None) -> tuple[bytes, str | None]:
    normalized_content_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if normalized_content_type not in {"application/x-tar", "application/octet-stream"}:
        return content, content_type
    buffer = io.BytesIO(content)
    if not tarfile.is_tarfile(buffer):
        return content, content_type
    buffer.seek(0)
    with tarfile.open(fileobj=buffer, mode="r:*") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        if not members:
            return content, content_type
        preferred = next(
            (
                member
                for member in members
                if Path(member.name).suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}
            ),
            members[0],
        )
        extracted = archive.extractfile(preferred)
        if extracted is None:
            return content, content_type
        file_content = extracted.read()
        if not file_content:
            return content, content_type
        guessed_type = mimetypes.guess_type(preferred.name)[0] or "application/octet-stream"
        return file_content, guessed_type


class MiniMaxAdapter(BaseProviderAdapter):
    def _route_group(self, ctx: dict[str, Any]) -> str | None:
        provider_model = ctx.get("provider_model")
        route_group = ctx.get("route_group")
        if isinstance(route_group, str) and route_group:
            return route_group
        value = getattr(provider_model, "route_group", None)
        return str(value) if value is not None else None

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = dict(ctx.get("payload") or {})
        route_group = self._route_group(ctx)
        if route_group == "minimax_voice_clone":
            return payload
        if route_group == "minimax_t2a_async":
            return payload
        if route_group == "minimax_video":
            return self._build_video_request(payload)
        return payload

    def _build_video_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload: dict[str, Any] = {
            "model": payload["model"],
        }
        prompt = payload.get("prompt")
        if prompt is not None:
            request_payload["prompt"] = prompt

        seconds = payload.get("seconds", payload.get("duration"))
        if seconds is not None:
            request_payload["duration"] = int(seconds)

        for key in ("resolution", "aspect_ratio", "prompt_optimizer", "fast_pretreatment", "callback_url"):
            value = payload.get(key)
            if value is not None:
                request_payload[key] = value

        input_mode = detect_minimax_video_input_mode(payload)
        if input_mode == "first_last_frame":
            request_payload["first_frame_image"] = (
                payload.get("first_frame")
                or payload.get("firstFrame")
                or payload.get("first_frame_image")
                or payload.get("input_reference")
                or payload.get("image_url")
                or payload.get("image")
            )
            request_payload["last_frame_image"] = (
                payload.get("last_frame") or payload.get("lastFrame") or payload.get("last_frame_image")
            )
        elif input_mode == "image":
            request_payload["first_frame_image"] = (
                payload.get("input_reference")
                or payload.get("first_frame")
                or payload.get("firstFrame")
                or payload.get("first_frame_image")
                or payload.get("image_url")
                or payload.get("image")
            )

        return request_payload

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        if not isinstance(resp, dict):
            return {"provider_raw": resp}

        provider_model = ctx.get("provider_model")
        route_group = self._route_group(ctx)
        payload = ctx.get("payload") or {}
        path = str(ctx.get("path") or "")

        if route_group == "minimax_voice_clone":
            if path == "/v1/voice_clone":
                return {
                    "voice_id": payload.get("voice_id"),
                    "model": payload.get("model"),
                    "demo_audio": resp.get("demo_audio"),
                    "input_sensitive": resp.get("input_sensitive"),
                    "input_sensitive_type": resp.get("input_sensitive_type"),
                    "provider_raw": resp,
                }
            if path == "/v1/get_voice":
                return {
                    "system_voice": resp.get("system_voice") or [],
                    "voice_cloning": resp.get("voice_cloning") or [],
                    "voice_generation": resp.get("voice_generation") or [],
                    "provider_raw": resp,
                }
            return resp

        if route_group == "minimax_t2a_async":
            if path == "/v1/t2a_async_v2":
                return {
                    "id": str(resp.get("task_id")),
                    "status": "submitted",
                    "provider_status": "submitted",
                    "file_id": str(resp.get("file_id")) if resp.get("file_id") is not None else None,
                    "usage_characters": resp.get("usage_characters"),
                    "model": payload.get("model"),
                    "created_at": int(datetime.now(timezone.utc).timestamp()),
                    "provider_raw": resp,
                }
            if path.startswith("/v1/query/t2a_async_query_v2"):
                raw_status = resp.get("status")
                return {
                    "id": str(resp.get("task_id")),
                    "status": _minimax_task_status(raw_status),
                    "provider_status": str(raw_status).lower() if raw_status is not None else None,
                    "file_id": str(resp.get("file_id")) if resp.get("file_id") is not None else None,
                    "model": getattr(provider_model, "model_code", None),
                    "provider_raw": resp,
                }

        if route_group == "minimax_video":
            if path == "/v1/video_generation":
                return {
                    "id": str(resp.get("task_id")),
                    "object": "video",
                    "status": "submitted",
                    "provider_status": "submitted",
                    "file_id": str(resp.get("file_id")) if resp.get("file_id") is not None else None,
                    "model": payload.get("model"),
                    "created_at": int(datetime.now(timezone.utc).timestamp()),
                    "seconds": str(payload.get("seconds") or payload.get("duration")) if payload.get("seconds") or payload.get("duration") else None,
                    "size": payload.get("resolution"),
                    "provider_raw": resp,
                }
            if path.startswith("/v1/query/video_generation"):
                raw_status = resp.get("status")
                width = resp.get("video_width")
                height = resp.get("video_height")
                size = None
                if width and height:
                    size = f"{width}x{height}"
                return {
                    "id": str(resp.get("task_id")),
                    "object": "video",
                    "status": _minimax_task_status(raw_status),
                    "provider_status": str(raw_status).lower() if raw_status is not None else None,
                    "file_id": str(resp.get("file_id")) if resp.get("file_id") is not None else None,
                    "model": getattr(provider_model, "model_code", None),
                    "size": size,
                    "provider_raw": resp,
                }

        return resp

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "minimax", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "minimax", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "minimax", "task_status": ctx}

    def _auth_headers(self, provider) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {provider.auth_config.get('api_key', '')}",
        }

    async def _download_external_file(self, url: str) -> tuple[bytes, str, str]:
        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "api35/0.1 (+https://api35.local)",
                    "Accept": "*/*",
                },
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
            filename = Path(urlparse(url).path).name or "minimax_audio"
            return response.content, content_type, filename

    async def _upload_file(self, *, provider, file_url: str, purpose: str) -> int:
        content, content_type, filename = await self._download_external_file(file_url)
        timeout = httpx.Timeout(180.0)
        headers = {
            "Authorization": f"Bearer {provider.auth_config.get('api_key', '')}",
        }
        data = {"purpose": purpose}
        files = {"file": (filename, content, content_type)}
        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout) as client:
            response = await client.post("/v1/files/upload", headers=headers, data=data, files=files)
            response.raise_for_status()
            payload = response.json()
            _raise_for_base_resp(payload)
            file_id = payload.get("file", {}).get("file_id")
            if file_id is None:
                raise httpx.HTTPError("minimax_file_upload_missing_file_id")
            return int(file_id)

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        provider = ctx["provider"]
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        file_id = result_payload.get("file_id")
        if file_id is None:
            raise httpx.HTTPError("minimax_file_not_ready")

        timeout = httpx.Timeout(180.0)
        headers = self._auth_headers(provider)
        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout, follow_redirects=True) as client:
            retrieve_response = await client.get("/v1/files/retrieve", headers=headers, params={"file_id": file_id})
            retrieve_response.raise_for_status()
            retrieve_payload = retrieve_response.json()
            _raise_for_base_resp(retrieve_payload)
            download_url = retrieve_payload.get("file", {}).get("download_url")
            if not download_url:
                raise httpx.HTTPError("minimax_download_url_not_found")
            content_response = await client.get(download_url)
            content_response.raise_for_status()
            return _unwrap_single_file_tar(
                content_response.content,
                content_response.headers.get("content-type"),
            )

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        path = str(ctx.get("path") or "")
        method = str(ctx.get("method", "POST")).upper()
        route_group = self._route_group(ctx)
        timeout = httpx.Timeout(180.0)
        headers = {
            **self._auth_headers(provider),
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {}

        if method != "GET":
            payload = self.build_request(ctx)

        if route_group == "minimax_voice_clone" and path == "/v1/voice_clone":
            request_payload = dict(payload)
            audio_url = request_payload.pop("audio_url")
            prompt_audio_url = request_payload.pop("prompt_audio_url")
            prompt_text = request_payload.pop("prompt_text")
            request_payload["file_id"] = await self._upload_file(
                provider=provider,
                file_url=audio_url,
                purpose="voice_clone",
            )
            request_payload["clone_prompt"] = {
                "prompt_audio": await self._upload_file(
                    provider=provider,
                    file_url=prompt_audio_url,
                    purpose="prompt_audio",
                ),
                "prompt_text": prompt_text,
            }
            payload = request_payload

        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout) as client:
            if method == "GET":
                parsed = urlparse(path)
                request_path = parsed.path or path
                params = parse_qs(parsed.query, keep_blank_values=True)
                normalized_params = {
                    key: values[0] if len(values) == 1 else values
                    for key, values in params.items()
                }
                response = await client.get(request_path, headers=self._auth_headers(provider), params=normalized_params)
            else:
                response = await client.post(path, json=payload, headers=headers)
            response.raise_for_status()
            if not response.content:
                return {}
            response_payload = response.json()
            _raise_for_base_resp(response_payload)
            return self.parse_response(ctx, response_payload)
