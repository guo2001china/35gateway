from __future__ import annotations

from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


def _extract_responses_output_text(output_items: Any) -> str | None:
    if not isinstance(output_items, list):
        return None
    text_chunks: list[str] = []
    for item in output_items:
        if not isinstance(item, dict):
            continue
        content_items = item.get("content")
        if not isinstance(content_items, list):
            continue
        for content in content_items:
            if not isinstance(content, dict):
                continue
            if content.get("type") != "output_text":
                continue
            text = content.get("text")
            if isinstance(text, str) and text:
                text_chunks.append(text)
    if not text_chunks:
        return None
    return "".join(text_chunks)


def _normalize_responses_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    if not isinstance(result.get("output_text"), str) or not result.get("output_text"):
        output_text = _extract_responses_output_text(result.get("output"))
        if output_text:
            result["output_text"] = output_text
    return result


def _normalize_request_path(*, base_url: str, path: str) -> str:
    normalized_path = path.lstrip("/")
    normalized_base = base_url.rstrip("/")
    if normalized_base.endswith("/openai") and normalized_path.startswith("v1/"):
        return normalized_path[len("v1/") :]
    if normalized_base.endswith("/v1") and normalized_path.startswith("v1/"):
        return normalized_path[len("v1/") :]
    return normalized_path


class OpenAIAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict):
        payload = dict(ctx.get("payload") or {})
        model = payload.get("model")
        if isinstance(model, str) and model:
            provider_model = ctx.get("provider_model")
            execution_model_code = getattr(provider_model, "execution_model_code", None)
            payload["model"] = execution_model_code or model
        path = str(ctx.get("path") or "")
        if path == "/v1/videos":
            for key in ("seconds", "duration"):
                value = payload.get(key)
                if value is not None and not isinstance(value, str):
                    payload[key] = str(value)
        return payload

    def parse_response(self, ctx: dict, resp):
        return {"provider": "openai", "data": resp}

    def parse_error(self, ctx: dict, resp):
        return {"provider": "openai", "error": resp}

    def create_task(self, ctx: dict):
        return {"provider": "openai", "task": ctx}

    def query_task(self, ctx: dict):
        return {"provider": "openai", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        base_url = provider.base_url or "https://api.openai.com"
        path = _normalize_request_path(base_url=base_url, path=str(ctx["path"]))
        headers = {"Authorization": f"Bearer {api_key}"}
        if provider.auth_config.get("http_referer"):
            headers["HTTP-Referer"] = provider.auth_config["http_referer"]
        if provider.auth_config.get("x_title"):
            headers["X-Title"] = provider.auth_config["x_title"]
        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.get(path, headers=headers)
            response.raise_for_status()
            return response.content, response.headers.get("content-type")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        request_payload = self.build_request(ctx)
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        base_url = provider.base_url or "https://api.openai.com"
        path = _normalize_request_path(base_url=base_url, path=str(ctx["path"]))
        method = ctx.get("method", "POST").upper()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider.auth_config.get("http_referer"):
            headers["HTTP-Referer"] = provider.auth_config["http_referer"]
        if provider.auth_config.get("x_title"):
            headers["X-Title"] = provider.auth_config["x_title"]
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            if method == "GET":
                response = await client.get(path, headers=headers)
            else:
                response = await client.post(path, json=request_payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            result = _normalize_responses_result(result)
            public_model = ctx.get("payload", {}).get("model")
            if isinstance(result, dict) and isinstance(public_model, str) and public_model:
                upstream_model = result.get("model")
                if isinstance(upstream_model, str) and upstream_model and upstream_model != public_model:
                    result["provider_model"] = upstream_model
                result["model"] = public_model
            return result
