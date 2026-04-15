from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.provider_support import detect_banana_input_mode, detect_seedance_input_mode, detect_veo_input_mode
from app.domains.platform.providers.base import BaseProviderAdapter


class FalAdapter(BaseProviderAdapter):
    _QUEUE_SUBPATHS = {
        "image-to-video",
        "first-last-frame-to-video",
        "reference-to-video",
        "extend-video",
    }

    def _parse_int_duration(self, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str) and value.endswith("s"):
            value = value[:-1]
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _format_fal_duration(self, value: Any, *, suffix: bool) -> str | int | None:
        parsed = self._parse_int_duration(value)
        if parsed is None:
            return None
        if suffix:
            return f"{parsed}s"
        return parsed

    def _queue_base_url(self, provider: Any) -> str:
        return str(provider.auth_config.get("queue_base_url") or "https://queue.fal.run").rstrip("/")

    def _split_queue_path(self, path: str) -> tuple[str, str | None]:
        normalized = "/" + path.strip("/")
        for subpath in self._QUEUE_SUBPATHS:
            suffix = f"/{subpath}"
            if normalized.endswith(suffix):
                return normalized[: -len(suffix)], subpath
        return normalized, None

    def _build_queue_submit_response(
        self,
        *,
        payload: dict[str, Any],
        model_code: str,
        request_id: str,
        queue_payload: dict[str, Any],
        provider_raw: dict[str, Any],
    ) -> dict[str, Any]:
        now = int(datetime.now(timezone.utc).timestamp())
        return {
            "id": request_id,
            "object": "video",
            "status": "submitted",
            "provider_status": "SUBMITTED",
            "model": model_code,
            "created_at": now,
            "progress": 0,
            "seconds": str(payload.get("seconds") or payload.get("duration") or "4"),
            "size": payload.get("size"),
            "queue_position": queue_payload.get("queue_position"),
            "status_url": queue_payload.get("status_url"),
            "response_url": queue_payload.get("response_url"),
            "cancel_url": queue_payload.get("cancel_url"),
            "fal_model_id": queue_payload.get("fal_model_id"),
            "fal_subpath": queue_payload.get("fal_subpath"),
            "provider_raw": provider_raw,
        }

    def _parse_queue_status(self, status_payload: dict[str, Any], *, model_code: str, task_id: str) -> dict[str, Any]:
        raw_status = str(status_payload.get("status") or "").strip().upper()
        if raw_status in {"IN_QUEUE", "QUEUED"}:
            status = "queued"
        elif raw_status in {"IN_PROGRESS", "RUNNING"}:
            status = "processing"
        elif raw_status == "COMPLETED":
            status = "completed"
        elif raw_status in {"FAILED", "ERROR"}:
            status = "failed"
        elif raw_status in {"CANCELLED", "CANCELED"}:
            status = "cancelled"
        else:
            status = "submitted"

        return {
            "id": task_id,
            "object": "video",
            "status": status,
            "provider_status": raw_status or None,
            "model": model_code,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "progress": status_payload.get("progress"),
            "queue_position": status_payload.get("queue_position"),
            "response_url": status_payload.get("response_url"),
            "status_url": status_payload.get("status_url"),
            "cancel_url": status_payload.get("cancel_url"),
            "logs": status_payload.get("logs"),
            "metrics": status_payload.get("metrics"),
            "error": status_payload.get("error"),
            "provider_raw": {"queue_status": status_payload},
        }

    def _build_failed_queue_result(
        self,
        *,
        task_id: str,
        model_code: str,
        status_payload: dict[str, Any],
        error_message: str,
    ) -> dict[str, Any]:
        return {
            "id": task_id,
            "object": "video",
            "status": "failed",
            "provider_status": str(status_payload.get("status") or "FAILED").strip().upper(),
            "model": model_code,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "error": error_message,
            "response_url": status_payload.get("response_url"),
            "status_url": status_payload.get("status_url"),
            "cancel_url": status_payload.get("cancel_url"),
            "logs": status_payload.get("logs"),
            "metrics": status_payload.get("metrics"),
            "provider_raw": {"queue_status": status_payload, "result_error": error_message},
        }

    def _resolve_create_path(self, *, provider: Any, route_group: str, model_code: str, payload: dict[str, Any]) -> str:
        if route_group == "banana":
            input_mode = detect_banana_input_mode(payload)
            if model_code == "gemini-2.5-flash-image":
                path_map = {
                    "text": provider.auth_config.get("nano_banana_create_path", "/fal-ai/nano-banana"),
                    "edit": provider.auth_config.get("nano_banana_edit_path", "/fal-ai/nano-banana/edit"),
                }
            elif model_code == "gemini-3-pro-image-preview":
                path_map = {
                    "text": provider.auth_config.get("nano_banana_pro_create_path", "/fal-ai/nano-banana-pro"),
                    "edit": provider.auth_config.get("nano_banana_pro_edit_path", "/fal-ai/nano-banana-pro/edit"),
                }
            else:
                path_map = {
                    "text": provider.auth_config.get("nano_banana_2_create_path", "/fal-ai/nano-banana-2"),
                    "edit": provider.auth_config.get("nano_banana_2_edit_path", "/fal-ai/nano-banana-2/edit"),
                }
            create_path = path_map.get(input_mode)
            if not create_path:
                raise httpx.HTTPError(f"fal_nano_banana_input_mode_not_supported:{input_mode}")
            return create_path

        if route_group == "seedance":
            input_mode = detect_seedance_input_mode(payload)
            if model_code == "seedance-2.0":
                path_map = {
                    "text": provider.auth_config.get(
                        "seedance20_text_create_path",
                        "/bytedance/seedance-2.0/text-to-video",
                    ),
                    "image": provider.auth_config.get(
                        "seedance20_image_create_path",
                        "/bytedance/seedance-2.0/image-to-video",
                    ),
                }
            elif model_code == "seedance-2.0-fast":
                path_map = {
                    "text": provider.auth_config.get(
                        "seedance20_fast_text_create_path",
                        "/bytedance/seedance-2.0/fast/text-to-video",
                    ),
                    "image": provider.auth_config.get(
                        "seedance20_fast_image_create_path",
                        "/bytedance/seedance-2.0/fast/image-to-video",
                    ),
                }
            else:
                raise httpx.HTTPError(f"fal_seedance_model_not_supported:{model_code}")
            create_path = path_map.get(input_mode)
            if not create_path:
                raise httpx.HTTPError(f"fal_seedance_input_mode_not_supported:{input_mode}")
            return create_path

        if route_group == "veo3":
            input_mode = detect_veo_input_mode(payload)
            if model_code == "veo-3":
                path_map = {
                    "text": provider.auth_config.get("veo3_create_path", "/fal-ai/veo3"),
                    "image": provider.auth_config.get("veo3_image_create_path", "/fal-ai/veo3/image-to-video"),
                }
            else:
                path_map = {
                    "text": provider.auth_config.get("veo3_fast_create_path", "/fal-ai/veo3/fast"),
                    "image": provider.auth_config.get(
                        "veo3_fast_image_create_path",
                        "/fal-ai/veo3/fast/image-to-video",
                    ),
                }
            create_path = path_map.get(input_mode)
            if not create_path:
                raise httpx.HTTPError(f"fal_veo3_input_mode_not_supported:{input_mode}")
            return create_path

        if route_group == "veo31":
            input_mode = detect_veo_input_mode(payload)
            if model_code == "veo-3.1-generate-preview":
                path_map = {
                    "text": provider.auth_config.get("veo31_create_path", "/fal-ai/veo3.1"),
                    "image": provider.auth_config.get(
                        "veo31_image_create_path",
                        "/fal-ai/veo3.1/image-to-video",
                    ),
                    "first_last_frame": provider.auth_config.get(
                        "veo31_first_last_create_path",
                        "/fal-ai/veo3.1/first-last-frame-to-video",
                    ),
                    "reference_images": provider.auth_config.get(
                        "veo31_reference_create_path",
                        "/fal-ai/veo3.1/reference-to-video",
                    ),
                }
            else:
                path_map = {
                    "text": provider.auth_config.get("veo31_fast_create_path", "/fal-ai/veo3.1/fast"),
                    "image": provider.auth_config.get(
                        "veo31_fast_image_create_path",
                        "/fal-ai/veo3.1/fast/image-to-video",
                    ),
                    "first_last_frame": provider.auth_config.get(
                        "veo31_fast_first_last_create_path",
                        "/fal-ai/veo3.1/fast/first-last-frame-to-video",
                    ),
                    "extend_video": provider.auth_config.get(
                        "veo31_fast_extend_create_path",
                        "/fal-ai/veo3.1/fast/extend-video",
                    ),
                }
            create_path = path_map.get(input_mode)
            if not create_path:
                raise httpx.HTTPError(f"fal_veo31_input_mode_not_supported:{input_mode}")
            return create_path

        raise httpx.HTTPError(f"fal_route_group_not_supported:{route_group}")

    def _build_veo_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload: dict[str, Any] = {
            "prompt": payload["prompt"],
        }

        duration = self._format_fal_duration(payload.get("seconds"), suffix=True)
        if duration is None:
            duration = self._format_fal_duration(payload.get("duration"), suffix=True)
        if duration is not None:
            request_payload["duration"] = duration

        size = payload.get("size")
        if size == "1280x720":
            request_payload["aspect_ratio"] = "16:9"
            request_payload.setdefault("resolution", "720p")
        elif size == "720x1280":
            request_payload["aspect_ratio"] = "9:16"
            request_payload.setdefault("resolution", "720p")

        if payload.get("resolution") is not None:
            request_payload["resolution"] = payload["resolution"]
        if payload.get("aspect_ratio") is not None:
            request_payload["aspect_ratio"] = payload["aspect_ratio"]
        if payload.get("negative_prompt") is not None:
            request_payload["negative_prompt"] = payload["negative_prompt"]
        if payload.get("generate_audio") is not None:
            request_payload["generate_audio"] = payload["generate_audio"]
        if payload.get("seed") is not None:
            request_payload["seed"] = payload["seed"]
        if payload.get("auto_fix") is not None:
            request_payload["auto_fix"] = payload["auto_fix"]
        if payload.get("safety_tolerance") is not None:
            request_payload["safety_tolerance"] = str(payload["safety_tolerance"])

        input_mode = detect_veo_input_mode(payload)
        if input_mode == "image":
            request_payload["image_url"] = payload.get("input_reference") or payload.get("image_url") or payload.get("image")
        elif input_mode == "first_last_frame":
            request_payload["first_frame_url"] = (
                payload.get("first_frame")
                or payload.get("firstFrame")
                or payload.get("first_frame_url")
                or payload.get("input_reference")
                or payload.get("image_url")
                or payload.get("image")
            )
            request_payload["last_frame_url"] = (
                payload.get("last_frame") or payload.get("lastFrame") or payload.get("last_frame_url")
            )
        elif input_mode == "reference_images":
            request_payload["image_urls"] = (
                payload.get("reference_images")
                or payload.get("referenceImages")
                or payload.get("image_urls")
            )
        elif input_mode == "extend_video":
            request_payload["video_url"] = payload.get("video") or payload.get("video_url")

        return request_payload

    def _build_banana_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload: dict[str, Any] = {
            "prompt": payload["prompt"],
        }
        if payload.get("aspect_ratio") is not None:
            request_payload["aspect_ratio"] = payload["aspect_ratio"]
        if payload.get("resolution") is not None:
            request_payload["resolution"] = payload["resolution"]
        if payload.get("num_images") is not None:
            request_payload["num_images"] = payload["num_images"]
        if payload.get("output_format") is not None:
            request_payload["output_format"] = payload["output_format"]
        if payload.get("enable_web_search") is not None:
            request_payload["enable_web_search"] = payload["enable_web_search"]
        if detect_banana_input_mode(payload) == "edit":
            request_payload["image_urls"] = payload.get("image_urls") or payload.get("input_images")
        return request_payload

    def _build_seedance_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        request_payload: dict[str, Any] = {
            "prompt": payload["prompt"],
        }
        if payload.get("resolution") is not None:
            request_payload["resolution"] = payload["resolution"]
        if payload.get("aspect_ratio") is not None:
            request_payload["aspect_ratio"] = payload["aspect_ratio"]
        if payload.get("seconds") is not None:
            request_payload["duration"] = str(payload["seconds"])
        if payload.get("generate_audio") is not None:
            request_payload["generate_audio"] = payload["generate_audio"]
        if payload.get("seed") is not None:
            request_payload["seed"] = payload["seed"]
        if ctx.get("end_user_id") is not None:
            request_payload["end_user_id"] = ctx["end_user_id"]
        if detect_seedance_input_mode(payload) == "image":
            request_payload["image_url"] = (
                payload.get("input_reference")
                or payload.get("image_url")
                or payload.get("image")
            )
        return request_payload

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        provider_model = ctx.get("provider_model")
        route_group = getattr(provider_model, "route_group", None)
        if route_group == "banana":
            return self._build_banana_request(payload)
        if route_group == "seedance":
            return self._build_seedance_request(ctx)
        if route_group in {"veo3", "veo31"}:
            return self._build_veo_request(payload)
        raise httpx.HTTPError(f"fal_route_group_not_supported:{route_group}")

    def _public_model_code(self, ctx: dict[str, Any]) -> str:
        return self.require_public_model_code(ctx)

    def _execution_model_code(self, ctx: dict[str, Any]) -> str:
        return self.require_execution_model_code(ctx)

    def parse_response(self, ctx: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
        payload = ctx.get("payload") or {}
        model_code = self._public_model_code(ctx)
        provider_model = ctx.get("provider_model")
        route_group = getattr(provider_model, "route_group", None)
        if route_group == "banana":
            image_items = resp.get("images") or []
            if not image_items and resp.get("image"):
                image_items = [resp["image"]]
            images = []
            for item in image_items:
                if isinstance(item, dict):
                    images.append(
                        {
                            "url": item.get("url"),
                            "width": item.get("width"),
                            "height": item.get("height"),
                            "content_type": item.get("content_type") or item.get("mime_type"),
                        }
                    )
            return {
                "object": "image_generation",
                "created_at": int(datetime.now(timezone.utc).timestamp()),
                "model": model_code,
                "images": images,
                "description": resp.get("description"),
                "provider_raw": resp,
            }
        if route_group == "seedance" and resp.get("request_id"):
            queue_payload = {
                "request_id": resp.get("request_id"),
                "queue_position": resp.get("queue_position"),
                "status_url": resp.get("status_url"),
                "response_url": resp.get("response_url"),
                "cancel_url": resp.get("cancel_url"),
                "fal_model_id": ctx.get("fal_model_id"),
                "fal_subpath": ctx.get("fal_subpath"),
            }
            return self._build_queue_submit_response(
                payload=payload,
                model_code=model_code,
                request_id=str(resp.get("request_id")),
                queue_payload=queue_payload,
                provider_raw=resp,
            )
        if resp.get("request_id"):
            queue_payload = {
                "request_id": resp.get("request_id"),
                "queue_position": resp.get("queue_position"),
                "status_url": resp.get("status_url"),
                "response_url": resp.get("response_url"),
                "cancel_url": resp.get("cancel_url"),
                "fal_model_id": ctx.get("fal_model_id"),
                "fal_subpath": ctx.get("fal_subpath"),
            }
            return self._build_queue_submit_response(
                payload=payload,
                model_code=model_code,
                request_id=str(resp.get("request_id")),
                queue_payload=queue_payload,
                provider_raw=resp,
            )
        video = resp.get("video") or {}
        queue_status = ctx.get("fal_queue_status") or {}
        return {
            "id": queue_status.get("request_id") or resp.get("video_id") or video.get("url"),
            "object": "video",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "status": "completed",
            "model": model_code,
            "progress": 100,
            "seconds": str(payload.get("seconds") or payload.get("duration") or "4"),
            "size": payload.get("size"),
            "url": video.get("url"),
            "error": None,
            "video": video,
            "thumbnail": resp.get("thumbnail"),
            "spritesheet": resp.get("spritesheet"),
            "response_url": queue_status.get("response_url"),
            "status_url": queue_status.get("status_url"),
            "cancel_url": queue_status.get("cancel_url"),
            "logs": queue_status.get("logs"),
            "metrics": queue_status.get("metrics"),
            "provider_status": queue_status.get("status"),
            "provider_raw": {
                "queue_status": queue_status,
                "response": resp,
            }
            if queue_status
            else resp,
        }

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        return {"provider": "fal", "error": resp}

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "fal", "task": ctx}

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"provider": "fal", "task_status": ctx}

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        task = ctx["provider_model"]
        result_payload = getattr(task, "result_payload", None) or {}
        video = result_payload.get("video") or {}
        video_url = video.get("url") or result_payload.get("url")
        if not video_url:
            raise httpx.HTTPError("fal_video_url_not_found")

        timeout = httpx.Timeout(120.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content, response.headers.get("content-type") or video.get("content_type")

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        provider = ctx["provider"]
        provider_model = ctx.get("provider_model")
        payload = ctx.get("payload") or {}
        method = ctx.get("method", "POST").upper()
        route_group = ctx.get("route_group") or getattr(provider_model, "route_group", None)

        if method == "GET" and route_group not in {"veo3", "veo31", "seedance"}:
            task = ctx["provider_model"]
            result_payload = getattr(task, "result_payload", None)
            if not result_payload:
                raise httpx.HTTPError("fal_task_result_not_found")
            return result_payload

        headers = {
            "Authorization": f"Key {provider.auth_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(180.0)

        if route_group in {"veo3", "veo31", "seedance"}:
            queue_base_url = self._queue_base_url(provider)
            if method == "GET":
                task = ctx["provider_model"]
                result_payload = getattr(task, "result_payload", None) or {}
                status_url = result_payload.get("status_url")
                response_url = result_payload.get("response_url")
                cancel_url = result_payload.get("cancel_url")
                if not status_url or not response_url or not cancel_url:
                    execution_model_code = self._execution_model_code(ctx)
                    create_path = self._resolve_create_path(
                        provider=provider,
                        route_group=route_group,
                        model_code=execution_model_code,
                        payload=payload,
                    )
                    create_model_path, _ = self._split_queue_path(create_path)
                    status_url = status_url or f"{queue_base_url}{create_model_path}/requests/{task.provider_task_id}/status"
                    response_url = response_url or f"{queue_base_url}{create_model_path}/requests/{task.provider_task_id}"
                    cancel_url = cancel_url or f"{queue_base_url}{create_model_path}/requests/{task.provider_task_id}/cancel"

                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    status_response = await client.get(status_url, headers={"Authorization": headers["Authorization"]})
                    status_response.raise_for_status()
                    status_payload = status_response.json() if status_response.content else {}
                    status_payload.setdefault("request_id", task.provider_task_id)
                    status_payload.setdefault("status_url", status_url)
                    status_payload.setdefault("response_url", response_url)
                    status_payload.setdefault("cancel_url", cancel_url)

                    parsed_status = self._parse_queue_status(
                        status_payload,
                        model_code=self._public_model_code(ctx),
                        task_id=str(task.provider_task_id or ""),
                    )
                    if parsed_status["status"] != "completed":
                        return parsed_status

                    if status_payload.get("error"):
                        return self._build_failed_queue_result(
                            task_id=str(task.provider_task_id or ""),
                            model_code=self._public_model_code(ctx),
                            status_payload=status_payload,
                            error_message=str(status_payload.get("error")),
                        )

                    try:
                        result_response = await client.get(
                            response_url,
                            headers={"Authorization": headers["Authorization"]},
                        )
                        result_response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        error_message = exc.response.text or str(exc)
                        return self._build_failed_queue_result(
                            task_id=str(task.provider_task_id or ""),
                            model_code=self._public_model_code(ctx),
                            status_payload=status_payload,
                            error_message=error_message,
                        )

                    result_payload = result_response.json() if result_response.content else {}
                    response_body = (
                        result_payload.get("response", result_payload)
                        if isinstance(result_payload, dict)
                        else result_payload
                    )
                    if not isinstance(response_body, dict):
                        response_body = {"data": response_body}
                    return self.parse_response(
                        {
                            **ctx,
                            "fal_queue_status": status_payload,
                        },
                        response_body,
                    )

            execution_model_code = self._execution_model_code(ctx)
            create_path = self._resolve_create_path(
                provider=provider,
                route_group=route_group,
                model_code=execution_model_code,
                payload=payload,
            )
            create_model_path, create_subpath = self._split_queue_path(create_path)
            async with httpx.AsyncClient(base_url=queue_base_url, timeout=timeout, follow_redirects=True) as client:
                response = await client.post(
                    create_path,
                    json=self.build_request(ctx),
                    headers=headers,
                )
                response.raise_for_status()
                response_payload = response.json() if response.content else {}
                return self.parse_response(
                    {
                        **ctx,
                        "fal_model_id": create_model_path,
                        "fal_subpath": create_subpath,
                    },
                    response_payload,
                )

        base_url = provider.base_url or "https://fal.run"
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post(
                create_path,
                json=self.build_request(ctx),
                headers=headers,
            )
            response.raise_for_status()
            return self.parse_response(ctx, response.json())
