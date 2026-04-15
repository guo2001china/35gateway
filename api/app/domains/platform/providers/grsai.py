from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.provider_support import detect_banana_input_mode
from app.domains.platform.providers.base import BaseProviderAdapter


class GRSAIAdapter(BaseProviderAdapter):
    _MODEL_NAME_MAP = {
        "gemini-2.5-flash-image": "nano-banana",
        "gemini-3-pro-image-preview": "nano-banana-pro",
        "gemini-3.1-flash-image-preview": "nano-banana-2",
    }

    def _provider_model_name(self, ctx: dict[str, Any]) -> str:
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "model_code", None)
        return self._MODEL_NAME_MAP.get(model_code, "nano-banana")

    def _build_banana_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        request_payload: dict[str, Any] = {
            "model": self._provider_model_name(ctx),
            "prompt": payload["prompt"],
        }
        if payload.get("aspect_ratio") is not None:
            request_payload["aspectRatio"] = payload["aspect_ratio"]
        if payload.get("resolution") is not None:
            request_payload["imageSize"] = payload["resolution"]
        if payload.get("webhook") is not None:
            request_payload["webHook"] = payload["webhook"]
        elif payload.get("webhook_url") is not None:
            request_payload["webHook"] = payload["webhook_url"]
        elif payload.get("webHook") is not None:
            request_payload["webHook"] = payload["webHook"]
        if payload.get("shut_progress") is not None:
            request_payload["shutProgress"] = payload["shut_progress"]
        elif payload.get("shutProgress") is not None:
            request_payload["shutProgress"] = payload["shutProgress"]
        if detect_banana_input_mode(payload) == "edit":
            request_payload["urls"] = payload.get("image_urls") or payload.get("input_images")
        return request_payload

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return self._build_banana_request(ctx)

    def parse_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "model_code", None) or payload.get("model")

        images: list[dict[str, Any]] = []
        for item in self._collect_image_items(resp):
            if isinstance(item, dict):
                images.append(
                    {
                        "url": item.get("url") or item.get("image_url"),
                        "b64_json": item.get("b64_json") or item.get("base64") or item.get("b64"),
                        "width": item.get("width"),
                        "height": item.get("height"),
                        "content_type": item.get("content_type") or item.get("mime_type"),
                    }
                )
            elif isinstance(item, str):
                if item.startswith("http://") or item.startswith("https://"):
                    images.append({"url": item})
                else:
                    images.append({"b64_json": item})

        return {
            "object": "image_generation",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "model": model_code,
            "images": images,
            "description": resp.get("description") or resp.get("message"),
            "provider_raw": resp,
        }

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "grsai", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "grsai", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "grsai", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        raise NotImplementedError

    def _extract_task_id(self, payload: dict[str, Any]) -> str | None:
        for key in ("task_id", "taskId", "id", "request_id", "requestId", "draw_id", "drawId"):
            value = payload.get(key)
            if value:
                return str(value)
        data = payload.get("data")
        if isinstance(data, dict):
            return self._extract_task_id(data)
        return None

    def _load_response_payload(self, response: httpx.Response) -> dict[str, Any]:
        content_type = (response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type == "text/event-stream":
            last_payload: dict[str, Any] | None = None
            for raw_line in response.text.splitlines():
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    last_payload = parsed
            if last_payload is None:
                raise httpx.HTTPError("grsai_empty_event_stream")
            return last_payload
        try:
            payload = response.json()
        except ValueError as exc:
            raise httpx.HTTPError("grsai_invalid_response_payload") from exc
        if not isinstance(payload, dict):
            raise httpx.HTTPError("grsai_invalid_response_payload")
        return payload

    def _collect_image_items(self, payload: Any) -> list[Any]:
        if isinstance(payload, dict):
            for key in ("images", "results", "output", "data"):
                value = payload.get(key)
                if isinstance(value, list) and value:
                    return value
                if isinstance(value, dict):
                    nested = self._collect_image_items(value)
                    if nested:
                        return nested
            if any(key in payload for key in ("url", "image_url", "base64", "b64", "b64_json")):
                return [payload]
        elif isinstance(payload, list):
            return payload
        return []

    def _is_terminal_success(self, payload: dict[str, Any]) -> bool:
        status = str(payload.get("status") or payload.get("state") or "").lower()
        if status in {"succeeded", "success", "completed", "done"}:
            return True
        return bool(self._collect_image_items(payload))

    def _is_terminal_failure(self, payload: dict[str, Any]) -> bool:
        status = str(payload.get("status") or payload.get("state") or "").lower()
        return status in {"failed", "error", "cancelled", "canceled"}

    async def _poll_result(
        self,
        *,
        client: httpx.AsyncClient,
        result_path: str,
        task_id: str,
        headers: dict[str, str],
        poll_interval: float,
        poll_timeout: float,
    ) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + poll_timeout
        request_payload = {
            "task_id": task_id,
            "taskId": task_id,
            "id": task_id,
            "request_id": task_id,
        }
        while True:
            response = await client.post(result_path, json=request_payload, headers=headers)
            response.raise_for_status()
            payload = self._load_response_payload(response)
            if self._is_terminal_success(payload):
                return payload
            if self._is_terminal_failure(payload):
                raise httpx.HTTPError(str(payload.get("error") or payload.get("message") or "grsai_task_failed"))
            if asyncio.get_running_loop().time() >= deadline:
                raise httpx.HTTPError("grsai_result_timeout")
            await asyncio.sleep(poll_interval)

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        headers = {
            "Authorization": f"Bearer {provider.auth_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(120.0)
        create_path = provider.auth_config.get("banana_create_path", "/v1/draw/nano-banana")
        result_path = provider.auth_config.get("banana_result_path", "/v1/draw/result")
        poll_interval = float(provider.auth_config.get("banana_poll_interval_seconds", "2"))
        poll_timeout = float(provider.auth_config.get("banana_poll_timeout_seconds", "60"))

        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout) as client:
            create_response = await client.post(
                create_path,
                json=self.build_request(ctx),
                headers=headers,
            )
            create_response.raise_for_status()
            create_payload = self._load_response_payload(create_response)

            if self._is_terminal_success(create_payload):
                return self.parse_response(ctx, create_payload)

            task_id = self._extract_task_id(create_payload)
            if not task_id:
                raise httpx.HTTPError("grsai_task_id_not_found")

            result_payload = await self._poll_result(
                client=client,
                result_path=result_path,
                task_id=task_id,
                headers=headers,
                poll_interval=poll_interval,
                poll_timeout=poll_timeout,
            )
            return self.parse_response(ctx, result_payload)
