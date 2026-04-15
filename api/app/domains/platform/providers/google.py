from __future__ import annotations

import base64
import mimetypes
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.provider_support import detect_banana_input_mode
from app.domains.platform.providers.base import BaseProviderAdapter


class GoogleAdapter(BaseProviderAdapter):
    def _resolve_model_path(self, ctx: dict[str, Any], path: str) -> str:
        provider_model = ctx.get("provider_model")
        execution_model_code = getattr(provider_model, "execution_model_code", None)
        public_model_code = getattr(provider_model, "public_model_code", None) or (ctx.get("payload") or {}).get("model")
        if not execution_model_code or not public_model_code or public_model_code == execution_model_code:
            return path
        return path.replace(f"/models/{public_model_code}:", f"/models/{execution_model_code}:")

    def _normalize_image_size(self, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).upper()
        if normalized in {"512", "1K", "2K", "4K"}:
            return normalized
        return None

    def _guess_mime_type(self, source: str, default: str = "image/png") -> str:
        guessed, _ = mimetypes.guess_type(source)
        return guessed or default

    def _build_image_part_from_data_url(self, value: str) -> dict[str, Any]:
        header, _, encoded = value.partition(",")
        mime_type = "image/png"
        if ";base64" in header and ":" in header:
            mime_type = header.split(":", 1)[1].split(";", 1)[0] or mime_type
        return {
            "inlineData": {
                "mimeType": mime_type,
                "data": encoded,
            }
        }

    async def _build_image_part_from_url(self, url: str) -> dict[str, Any]:
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "").split(";", 1)[0] or self._guess_mime_type(url)
            return {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": base64.b64encode(response.content).decode("ascii"),
                }
            }

    async def _build_image_part(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            inline_data = item.get("inlineData") or item.get("inline_data")
            if isinstance(inline_data, dict) and inline_data.get("data"):
                mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"
                return {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": inline_data["data"],
                    }
                }
            image_url = item.get("image_url") or item.get("url")
            if image_url:
                return await self._build_image_part(str(image_url))

        if not isinstance(item, str):
            raise httpx.HTTPError("google_image_input_invalid")
        if item.startswith("data:image/"):
            return self._build_image_part_from_data_url(item)
        return await self._build_image_part_from_url(item)

    async def _build_banana_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "public_model_code", None) or payload.get("model")
        contents_parts: list[dict[str, Any]] = [{"text": payload["prompt"]}]

        input_mode = detect_banana_input_mode(payload)
        if input_mode == "edit":
            image_urls = payload.get("image_urls") or payload.get("input_images") or []
            for item in image_urls:
                contents_parts.append(await self._build_image_part(item))

        generation_config: dict[str, Any] = {}
        image_config: dict[str, Any] = {}

        aspect_ratio = payload.get("aspect_ratio")
        if aspect_ratio:
            image_config["aspectRatio"] = str(aspect_ratio)

        image_size = self._normalize_image_size(payload.get("resolution"))
        if image_size and model_code in {
            "gemini-3-pro-image-preview",
            "gemini-3.1-flash-image-preview",
        }:
            image_config["imageSize"] = image_size

        if image_config:
            generation_config["imageConfig"] = image_config

        request_payload: dict[str, Any] = {
            "contents": [{"parts": contents_parts}],
        }
        if generation_config:
            request_payload["generationConfig"] = generation_config
        return request_payload

    def build_request(self, ctx: dict[str, Any]):
        return ctx.get("payload")

    def parse_response(self, ctx: dict[str, Any], resp):
        return {"provider": "google", "data": resp}

    def parse_error(self, ctx: dict[str, Any], resp):
        return {"provider": "google", "error": resp}

    def create_task(self, ctx: dict):
        return {"provider": "google", "task": ctx}

    def query_task(self, ctx: dict):
        return {"provider": "google", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        raise NotImplementedError

    def _parse_banana_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "model_code", None) or payload.get("model")
        images: list[dict[str, Any]] = []
        texts: list[str] = []
        for candidate in resp.get("candidates", []):
            content = candidate.get("content") or {}
            for part in content.get("parts", []):
                inline_data = part.get("inlineData") or {}
                if inline_data.get("data"):
                    images.append(
                        {
                            "b64_json": inline_data["data"],
                            "mime_type": inline_data.get("mimeType"),
                        }
                    )
                if part.get("text"):
                    texts.append(part["text"])
        return {
            "object": "image_generation",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "model": model_code,
            "images": images,
            "description": "\n".join(texts).strip() or None,
            "provider_raw": resp,
        }

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        provider_model = ctx.get("provider_model")
        route_group = getattr(provider_model, "route_group", None)
        api_key = provider.auth_config.get("api_key", "")
        base_url = provider.base_url or "https://generativelanguage.googleapis.com"
        path = self._resolve_model_path(ctx, ctx["path"])
        method = ctx.get("method", "POST").upper()
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(60.0)
        if route_group == "banana":
            request_payload = await self._build_banana_request(ctx)
        else:
            request_payload = self.build_request(ctx)

        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            if method == "GET":
                response = await client.get(path, headers=headers)
            else:
                response = await client.post(path, json=request_payload, headers=headers)
            response.raise_for_status()
            payload = response.json()
            if route_group == "banana":
                return self._parse_banana_response(ctx, payload)
            return payload
