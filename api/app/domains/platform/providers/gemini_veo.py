from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.domains.platform.providers.base import BaseProviderAdapter


class GeminiVeoAdapter(BaseProviderAdapter):
    def _parse_duration(self, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str) and value.endswith("s"):
            value = value[:-1]
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}

        instance: dict[str, Any] = {}
        if payload.get("prompt"):
            instance["prompt"] = payload["prompt"]

        image_input = (
            payload.get("first_frame")
            or payload.get("firstFrame")
            or payload.get("first_frame_url")
            or payload.get("input_reference")
            or payload.get("image_url")
            or payload.get("image")
        )
        if image_input is not None:
            instance["image"] = image_input

        last_frame = payload.get("last_frame") or payload.get("lastFrame") or payload.get("last_frame_url")
        if last_frame is not None:
            instance["lastFrame"] = last_frame

        reference_images = (
            payload.get("reference_images")
            or payload.get("referenceImages")
            or payload.get("image_urls")
        )
        if reference_images is not None:
            instance["referenceImages"] = reference_images

        video_input = payload.get("video") or payload.get("video_url")
        if video_input is not None:
            instance["video"] = video_input

        parameters: dict[str, Any] = {}

        size = payload.get("size")
        if size == "1280x720":
            parameters["aspectRatio"] = "16:9"
            parameters.setdefault("resolution", "720p")
        elif size == "720x1280":
            parameters["aspectRatio"] = "9:16"
            parameters.setdefault("resolution", "720p")

        if payload.get("aspect_ratio") is not None:
            parameters["aspectRatio"] = payload["aspect_ratio"]
        if payload.get("resolution") is not None:
            parameters["resolution"] = payload["resolution"]
        duration_seconds = self._parse_duration(payload.get("seconds"))
        if duration_seconds is None:
            duration_seconds = self._parse_duration(payload.get("duration"))
        if duration_seconds is not None:
            parameters["durationSeconds"] = duration_seconds
        if payload.get("number_of_videos") is not None:
            parameters["numberOfVideos"] = int(payload["number_of_videos"])
        if payload.get("person_generation") is not None:
            parameters["personGeneration"] = payload["person_generation"]
        if payload.get("negative_prompt") is not None:
            parameters["negativePrompt"] = payload["negative_prompt"]
        if payload.get("seed") is not None:
            parameters["seed"] = payload["seed"]

        request_body: dict[str, Any] = {"instances": [instance]}
        if parameters:
            request_body["parameters"] = parameters
        return request_body

    def parse_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        provider_model = ctx.get("provider_model")
        model_code = getattr(provider_model, "model_code", None) or "veo-3.1-generate-preview"

        done = bool(resp.get("done"))
        error_payload = resp.get("error")
        response_payload = resp.get("response") or {}
        generate_response = response_payload.get("generateVideoResponse") or {}
        generated_samples = generate_response.get("generatedSamples") or []
        generated_videos = response_payload.get("generatedVideos") or []
        results = generated_samples or generated_videos
        filtered_count = generate_response.get("raiMediaFilteredCount") or 0
        filtered_reasons = generate_response.get("raiMediaFilteredReasons") or []

        status = "processing"
        error_message = None
        if error_payload:
            status = "failed"
            error_message = str(error_payload)
        elif filtered_count and not results:
            status = "failed"
            error_message = "; ".join(filtered_reasons) or "veo3_generation_filtered"
        elif done:
            status = "completed"

        return {
            "id": resp.get("name"),
            "object": "video",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "status": status,
            "model": model_code,
            "progress": 100 if status == "completed" else 0,
            "results": results,
            "error": error_message,
            "provider_raw": resp,
        }

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "gemini_veo", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "gemini_veo", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "gemini_veo", "task_status": ctx}

    def _auth_headers(self, provider) -> dict[str, str]:
        return {
            "x-goog-api-key": provider.auth_config.get("api_key", ""),
            "Content-Type": "application/json",
        }

    def _predict_path(self, model_code: str) -> str:
        return f"/v1beta/models/{model_code}:predictLongRunning"

    async def _load_binary_payload(self, value: Any, default_mime_type: str) -> tuple[bytes, str] | None:
        if not isinstance(value, str):
            return None

        if value.startswith("data:") and ";base64," in value:
            prefix, encoded = value.split(",", 1)
            mime_type = prefix.split(";", 1)[0].replace("data:", "", 1) or default_mime_type
            return base64.b64decode(encoded), mime_type

        if value.startswith("http://") or value.startswith("https://"):
            timeout = httpx.Timeout(60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(value)
                response.raise_for_status()
                mime_type = response.headers.get("content-type", default_mime_type).split(";", 1)[0]
                return response.content, mime_type

        if os.path.exists(value):
            with open(value, "rb") as file_obj:
                return file_obj.read(), default_mime_type

        return None

    async def _materialize_media_input(
        self,
        *,
        value: Any,
        default_mime_type: str,
        bytes_key: str,
    ) -> Any:
        loaded = await self._load_binary_payload(value, default_mime_type)
        if loaded is None:
            return value
        data, mime_type = loaded
        return {
            "mimeType": mime_type,
            bytes_key: base64.b64encode(data).decode("utf-8"),
        }

    async def _normalize_instance(self, instance: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(instance)
        if normalized.get("image") is not None:
            normalized["image"] = await self._materialize_media_input(
                value=normalized["image"],
                default_mime_type="image/png",
                bytes_key="imageBytes",
            )
        if normalized.get("lastFrame") is not None:
            normalized["lastFrame"] = await self._materialize_media_input(
                value=normalized["lastFrame"],
                default_mime_type="image/png",
                bytes_key="imageBytes",
            )

        reference_images = normalized.get("referenceImages")
        if isinstance(reference_images, list):
            converted: list[dict[str, Any]] = []
            for item in reference_images:
                if isinstance(item, dict):
                    current = dict(item)
                else:
                    current = {"image": item, "referenceType": "asset"}
                if current.get("image") is not None:
                    current["image"] = await self._materialize_media_input(
                        value=current["image"],
                        default_mime_type="image/png",
                        bytes_key="imageBytes",
                    )
                converted.append(current)
            normalized["referenceImages"] = converted

        if normalized.get("video") is not None:
            normalized["video"] = await self._materialize_media_input(
                value=normalized["video"],
                default_mime_type="video/mp4",
                bytes_key="videoBytes",
            )

        return normalized

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        provider = ctx["provider"]
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        results = result_payload.get("results") or []
        if not results:
            result_payload = await self.invoke(
                {
                    "provider": provider,
                    "provider_model": task,
                    "method": "GET",
                }
            )
            results = result_payload.get("results") or []

        if not results:
            raise httpx.HTTPError("veo3_result_not_found")

        first = results[0]
        video = first.get("video") or first
        if video.get("videoBytes"):
            content = base64.b64decode(video["videoBytes"])
            return content, video.get("mimeType", "video/mp4")

        download_uri = video.get("uri")
        if not download_uri:
            raise httpx.HTTPError("veo3_download_uri_not_found")

        timeout = httpx.Timeout(180.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(download_uri, headers={"x-goog-api-key": provider.auth_config.get("api_key", "")})
            response.raise_for_status()
            return response.content, response.headers.get("content-type") or video.get("mimeType")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        provider_model = ctx["provider_model"]
        model_code = getattr(provider_model, "model_code", None) or "veo-3.1-generate-preview"
        method = ctx.get("method", "POST").upper()
        timeout = httpx.Timeout(180.0)
        base_url = provider.base_url or "https://generativelanguage.googleapis.com"

        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            if method == "GET":
                operation_name = getattr(provider_model, "provider_task_id", None) or ctx.get("provider_task_id")
                if not operation_name:
                    raise httpx.HTTPError("veo3_operation_name_not_found")
                response = await client.get(
                    f"/v1beta/{operation_name}",
                    headers={"x-goog-api-key": provider.auth_config.get("api_key", "")},
                )
                response.raise_for_status()
                return self.parse_response(ctx, response.json())

            request_payload = self.build_request(ctx)
            instance = request_payload["instances"][0]
            request_payload["instances"][0] = await self._normalize_instance(instance)

            response = await client.post(
                self._predict_path(model_code),
                json=request_payload,
                headers=self._auth_headers(provider),
            )
            response.raise_for_status()
            return self.parse_response(ctx, response.json())
