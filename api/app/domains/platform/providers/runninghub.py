from __future__ import annotations

from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


class RunningHubAdapter(BaseProviderAdapter):
    def build_request(self, ctx: dict):
        payload = ctx.get("payload") or {}
        request_payload = {
            "prompt": payload["prompt"],
            "size": payload.get("size", "720x1280"),
            "duration": str(payload.get("seconds") or payload.get("duration") or "4"),
        }
        webhook_url = payload.get("webhookUrl")
        if webhook_url:
            request_payload["webhookUrl"] = webhook_url
        return request_payload

    def parse_response(self, ctx: dict, resp):
        return resp

    def parse_error(self, ctx: dict, resp):
        return {"provider": "runninghub", "error": resp}

    def create_task(self, ctx: dict):
        return {"provider": "runninghub", "task": ctx}

    def query_task(self, ctx: dict):
        return {"provider": "runninghub", "task_status": ctx}

    def _normalize_status(self, status: str | None) -> str:
        mapping = {
            "QUEUED": "queued",
            "RUNNING": "processing",
            "SUCCESS": "completed",
            "FAILED": "failed",
        }
        if not status:
            return "submitted"
        return mapping.get(status.upper(), status.lower())

    def _normalize_task_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": raw.get("taskId"),
            "object": "video",
            "status": self._normalize_status(raw.get("status")),
            "errorCode": raw.get("errorCode"),
            "errorMessage": raw.get("errorMessage"),
            "results": raw.get("results"),
            "usage": raw.get("usage"),
            "clientId": raw.get("clientId"),
            "provider_raw": raw,
        }

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        query_path = provider.auth_config.get("video_query_path", "/openapi/v2/query")
        task_id = ctx["path"].split("/")[-2]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(
            base_url=provider.base_url or "https://www.runninghub.ai",
            timeout=timeout,
        ) as client:
            query_response = await client.post(query_path, json={"taskId": task_id}, headers=headers)
            query_response.raise_for_status()
            query_payload = query_response.json()
            results = query_payload.get("results") or []
            if not results or not results[0].get("url"):
                raise httpx.HTTPError("runninghub_result_url_not_found")
            file_response = await client.get(results[0]["url"])
            file_response.raise_for_status()
            return file_response.content, file_response.headers.get("content-type")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        api_key = provider.auth_config.get("api_key") or provider.auth_config.get("token", "")
        method = ctx.get("method", "POST").upper()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(120.0)
        base_url = provider.base_url or "https://www.runninghub.ai"
        create_path = provider.auth_config.get(
            "video_create_path", "/openapi/v2/rhart-video-s-official/text-to-video"
        )
        query_path = provider.auth_config.get("video_query_path", "/openapi/v2/query")

        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            if method == "GET":
                task_id = ctx["path"].split("/")[-1]
                response = await client.post(query_path, json={"taskId": task_id}, headers=headers)
                response.raise_for_status()
                return self._normalize_task_response(response.json())

            response = await client.post(
                create_path,
                json=self.build_request(ctx),
                headers=headers,
            )
            response.raise_for_status()
            return self._normalize_task_response(response.json())
