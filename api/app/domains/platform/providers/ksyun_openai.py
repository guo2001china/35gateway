from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import httpx

from app.core.provider_support import detect_banana_input_mode
from app.domains.platform.providers.openai import OpenAIAdapter, _normalize_request_path


class KsyunOpenAIAdapter(OpenAIAdapter):
    _THINK_BLOCK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

    def _resolve_public_model(self, ctx: dict[str, Any]) -> str | None:
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "public_model_code", None)
        if isinstance(model_code, str) and model_code:
            return model_code

        payload = ctx.get("payload") or {}
        model = payload.get("model")
        return model if isinstance(model, str) and model else None

    def _resolve_target_model(self, ctx: dict[str, Any]) -> str | None:
        provider_model = ctx.get("provider_model")
        for attr in ("execution_model_code", "public_model_code"):
            value = getattr(provider_model, attr, None)
            if isinstance(value, str) and value:
                return value
        return self._resolve_public_model(ctx)

    def _build_banana_prompt(self, payload: dict[str, Any]) -> str:
        prompt_lines = [str(payload.get("prompt") or "").strip()]
        # global-kspmas currently exposes these image models through chat/completions,
        # so explicit image knobs are folded into the prompt until Ksyun publishes
        # a structured image generation contract for them.
        aspect_ratio = payload.get("aspect_ratio")
        if aspect_ratio:
            prompt_lines.append(f"Output aspect ratio: {aspect_ratio}.")
        resolution = payload.get("resolution")
        if resolution:
            prompt_lines.append(f"Preferred resolution: {resolution}.")
        return "\n".join(line for line in prompt_lines if line)

    def _build_banana_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        content: list[dict[str, Any]] = [{"type": "text", "text": self._build_banana_prompt(payload)}]

        if detect_banana_input_mode(payload) == "edit":
            for item in payload.get("image_urls") or payload.get("input_images") or []:
                if isinstance(item, str) and item:
                    content.append({"type": "image_url", "image_url": {"url": item}})

        target_model = self._resolve_target_model(ctx)
        request_payload: dict[str, Any] = {
            "messages": [{"role": "user", "content": content}],
        }
        if target_model:
            request_payload["model"] = target_model
        return request_payload

    def _extract_message_text(self, message: dict[str, Any]) -> str | None:
        def _clean_text(value: str) -> str | None:
            text = self._THINK_BLOCK_PATTERN.sub("", value).strip()
            return text or None

        content = message.get("content")
        if isinstance(content, str):
            return _clean_text(content)
        if not isinstance(content, list):
            return None
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "text":
                continue
            text = str(item.get("text") or "").strip()
            if text:
                parts.append(text)
        if not parts:
            return None
        return _clean_text("\n".join(parts))

    def _extract_image_item(self, message: dict[str, Any]) -> dict[str, Any] | None:
        audio = message.get("audio")
        if isinstance(audio, dict):
            data = audio.get("data")
            if isinstance(data, str) and data:
                extra_content = audio.get("extra_content") or {}
                google_meta = extra_content.get("google") if isinstance(extra_content, dict) else {}
                mime_type = None
                if isinstance(google_meta, dict):
                    mime_type = google_meta.get("mime_type")
                if not mime_type and isinstance(extra_content, dict):
                    mime_type = extra_content.get("mime_type")
                if not mime_type:
                    mime_type = audio.get("mime_type")
                return {
                    "b64_json": data,
                    "mime_type": mime_type,
                }

        image = message.get("image")
        if isinstance(image, dict):
            data = image.get("b64_json") or image.get("data")
            if isinstance(data, str) and data:
                return {
                    "b64_json": data,
                    "mime_type": image.get("mime_type"),
                }
        return None

    def _parse_banana_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        images: list[dict[str, Any]] = []
        descriptions: list[str] = []

        for choice in resp.get("choices", []):
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            image_item = self._extract_image_item(message)
            if image_item is not None:
                images.append(image_item)
            text = self._extract_message_text(message)
            if text:
                descriptions.append(text)

        return {
            "object": "image_generation",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "model": self._resolve_public_model(ctx) or resp.get("model"),
            "images": images,
            "description": "\n".join(descriptions).strip() or None,
            "provider_raw": resp,
        }

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider_model = ctx.get("provider_model")
        route_group = getattr(provider_model, "route_group", None)
        if route_group != "banana":
            return await super().invoke(ctx)

        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        base_url = provider.base_url or "https://global-kspmas.ksyun.com/v1"
        path = _normalize_request_path(base_url=base_url, path="/v1/chat/completions")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        request_payload = self._build_banana_request(ctx)
        timeout = httpx.Timeout(180.0)

        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post(path, json=request_payload, headers=headers)
            response.raise_for_status()
            payload = response.json()
            return self._parse_banana_response(ctx, payload)
