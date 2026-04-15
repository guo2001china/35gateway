from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


class VolcengineAdapter(BaseProviderAdapter):
    def _build_seedream_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "model_code", None) or payload.get("model")

        request_payload: dict[str, Any] = {
            "model": model_code,
            "prompt": payload["prompt"],
            "response_format": payload.get("response_format") or "url",
        }

        image = payload.get("image")
        if image is None and payload.get("image_urls"):
            image_urls = payload.get("image_urls")
            if isinstance(image_urls, list):
                image = image_urls if len(image_urls) > 1 else image_urls[0]
        if image is not None:
            request_payload["image"] = image

        if payload.get("size") is not None:
            request_payload["size"] = payload["size"]
        if payload.get("stream") is not None:
            request_payload["stream"] = payload["stream"]
        if payload.get("watermark") is not None:
            request_payload["watermark"] = payload["watermark"]
        if payload.get("output_format") is not None:
            request_payload["output_format"] = payload["output_format"]
        if payload.get("tools") is not None:
            request_payload["tools"] = payload["tools"]
        if payload.get("sequential_image_generation") is not None:
            request_payload["sequential_image_generation"] = payload["sequential_image_generation"]
        if payload.get("sequential_image_generation_options") is not None:
            request_payload["sequential_image_generation_options"] = payload["sequential_image_generation_options"]
        if payload.get("optimize_prompt_options") is not None:
            request_payload["optimize_prompt_options"] = payload["optimize_prompt_options"]

        return request_payload

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return self._build_seedream_request(ctx)

    def parse_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        public_model = payload.get("model") or getattr(provider_model, "model_code", None)
        images: list[dict[str, Any]] = []
        for item in resp.get("data", []):
            if not isinstance(item, dict):
                continue
            images.append(
                {
                    "url": item.get("url"),
                    "b64_json": item.get("b64_json"),
                    "mime_type": item.get("mime_type") or "image/png",
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "content_type": item.get("content_type") or item.get("mime_type"),
                }
            )

        return {
            "object": "image_generation",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "model": public_model,
            "images": images,
            "description": resp.get("revised_prompt"),
            "provider_raw": resp,
        }

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "volcengine", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "volcengine", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "volcengine", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        raise NotImplementedError

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        headers = {
            "Authorization": f"Bearer {provider.auth_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(120.0)
        path = str(ctx.get("path") or provider.auth_config.get("images_generate_path") or "/images/generations")

        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout) as client:
            response = await client.post(
                path,
                json=self.build_request(ctx),
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise httpx.HTTPError("volcengine_invalid_response_payload")
            return self.parse_response(ctx, payload)
