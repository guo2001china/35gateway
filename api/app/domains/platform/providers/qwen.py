from __future__ import annotations

from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


class QwenAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = dict(ctx.get("payload") or {})
        model = payload.get("model")
        provider_model = ctx.get("provider_model")
        execution_model_code = getattr(provider_model, "execution_model_code", None)
        if isinstance(model, str) and model and isinstance(execution_model_code, str) and execution_model_code:
            payload["model"] = execution_model_code
        return payload

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        if isinstance(resp, dict):
            public_model = ctx.get("public_model")
            if not isinstance(public_model, str) or not public_model:
                payload = ctx.get("payload")
                if isinstance(payload, dict):
                    public_model = payload.get("model")
            path = str(ctx.get("path") or "")
            if (
                isinstance(public_model, str)
                and public_model
                and "multimodal-generation/generation" in path
            ):
                upstream_model = resp.get("model")
                if isinstance(upstream_model, str) and upstream_model and upstream_model != public_model:
                    resp["provider_model"] = upstream_model
                resp["model"] = public_model
        return resp

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "qwen", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "qwen", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "qwen", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        raise NotImplementedError

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        method = str(ctx.get("method", "POST")).upper()
        path = str(ctx["path"])
        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(base_url=provider.base_url, timeout=timeout) as client:
            response = await client.request(
                method,
                path,
                json=self.build_request(ctx) if method != "GET" else None,
                headers=headers,
            )
            response.raise_for_status()
            if not response.content:
                return {}
            return self.parse_response(ctx, response.json())
