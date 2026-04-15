from __future__ import annotations

from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


def _task_id_from_ctx(ctx: dict[str, Any]) -> str | None:
    provider_model = ctx.get("provider_model")
    provider_task_id = getattr(provider_model, "provider_task_id", None)
    if isinstance(provider_task_id, str) and provider_task_id:
        return provider_task_id
    return None


def _resolve_public_path(ctx: dict[str, Any]) -> str:
    task_id = _task_id_from_ctx(ctx)
    if task_id:
        return f"/v1/tasks/{task_id}"

    public_path = str(ctx.get("public_path") or "").strip()
    if public_path:
        return public_path

    path = str(ctx.get("path") or "").strip()
    if path:
        return path

    provider_model = ctx.get("provider_model")
    public_model_code = getattr(provider_model, "public_model_code", None)
    if isinstance(public_model_code, str) and public_model_code:
        return f"/v1/{public_model_code}"

    raise httpx.HTTPError("gateway35m_path_missing")


class Gateway35MAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        request_payload = ctx.get("forward_payload")
        if request_payload is None:
            request_payload = ctx.get("payload")
        return dict(request_payload or {})

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "35m", "data": resp}

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "35m", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "35m", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "35m", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        task_id = _task_id_from_ctx(ctx)
        if not task_id:
            raise httpx.HTTPError("gateway35m_task_id_missing")
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(base_url=provider.base_url.rstrip("/"), timeout=timeout) as client:
            response = await client.get(f"/v1/tasks/{task_id}/content", headers=headers)
            response.raise_for_status()
            return response.content, response.headers.get("content-type")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        payload = self.build_request(ctx)
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        method = str(ctx.get("public_method") or ctx.get("method") or "POST").upper()
        path = _resolve_public_path(ctx)
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = httpx.Timeout(180.0)

        async with httpx.AsyncClient(base_url=provider.base_url.rstrip("/"), timeout=timeout) as client:
            if method == "GET":
                response = await client.get(path, headers=headers, params=payload or None)
            elif method == "DELETE":
                if ctx.get("public_path") or _task_id_from_ctx(ctx):
                    response = await client.request("DELETE", path, headers=headers)
                else:
                    response = await client.request("DELETE", path, headers=headers, json=payload or None)
            else:
                response = await client.request(method, path, headers=headers, json=payload)
            response.raise_for_status()

            content_type = str(response.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                return response.json()
            return {"data": response.text}
