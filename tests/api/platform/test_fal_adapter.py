from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.domains.platform.providers.fal import FalAdapter


class _Response:
    def __init__(self, payload, *, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""
        self.content = b"{}"
        self.headers = {"content-type": "application/json"}
        self.request = httpx.Request("GET", "https://example.com")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                self.text or f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, text=self.text),
            )
        return None

    def json(self):
        return self._payload


class _QueueClient:
    def __init__(self, responses, *args, **kwargs):
        self.base_url = kwargs.get("base_url")
        self.timeout = kwargs.get("timeout")
        self.follow_redirects = kwargs.get("follow_redirects")
        self.calls: list[tuple[str, str, dict | None, dict[str, str] | None]] = []
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, path, json=None, headers=None):
        self.calls.append(("POST", path, json, headers))
        return self._responses.pop(0)

    async def get(self, path, headers=None):
        self.calls.append(("GET", path, None, headers))
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_fal_adapter_uses_queue_for_veo31_create(monkeypatch) -> None:
    adapter = FalAdapter()
    seen_kwargs: dict[str, object] = {}
    created_clients: list[_QueueClient] = []

    def _client_factory(*args, **kwargs):
        seen_kwargs.update(kwargs)
        client = _QueueClient(
            [
                _Response(
                    {
                        "request_id": "fal-req-123",
                        "status_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123/status",
                        "response_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123",
                        "cancel_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123/cancel",
                    }
                )
            ],
            *args,
            **kwargs,
        )
        created_clients.append(client)
        return client

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", _client_factory)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="veo-3.1-fast",
                execution_model_code="veo-3.1-fast-generate-preview",
                route_group="veo31",
            ),
            "payload": {
                "prompt": "make a short cinematic shot",
                "input_reference": "https://example.com/frame.png",
                "seconds": 6,
            },
            "method": "POST",
        }
    )

    assert seen_kwargs["base_url"] == "https://queue.fal.run"
    client = created_clients[0]
    assert client.calls == [
        (
            "POST",
            "/fal-ai/veo3.1/fast/image-to-video",
            {
                "prompt": "make a short cinematic shot",
                "duration": "6s",
                "image_url": "https://example.com/frame.png",
            },
            {
                "Authorization": "Key demo-key",
                "Content-Type": "application/json",
            },
        )
    ]
    assert result["id"] == "fal-req-123"
    assert result["status"] == "submitted"
    assert result["fal_model_id"] == "/fal-ai/veo3.1/fast"
    assert result["fal_subpath"] == "image-to-video"
    assert seen_kwargs["follow_redirects"] is True


@pytest.mark.asyncio
async def test_fal_adapter_uses_queue_for_seedance_fast_create(monkeypatch) -> None:
    adapter = FalAdapter()
    created_clients: list[_QueueClient] = []

    def _client_factory(*args, **kwargs):
        client = _QueueClient(
            [
                _Response(
                    {
                        "request_id": "seedance-req-123",
                        "status_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-req-123/status",
                        "response_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-req-123",
                        "cancel_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-req-123/cancel",
                    }
                )
            ],
            *args,
            **kwargs,
        )
        created_clients.append(client)
        return client

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", _client_factory)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="seedance-2.0-fast",
                execution_model_code="seedance-2.0-fast",
                route_group="seedance",
            ),
            "payload": {
                "prompt": "short cinematic video with ambient audio",
                "seconds": 4,
                "resolution": "720p",
            },
            "end_user_id": "user-9",
            "method": "POST",
        }
    )

    client = created_clients[0]
    assert client.calls == [
        (
            "POST",
            "/bytedance/seedance-2.0/fast/text-to-video",
            {
                "prompt": "short cinematic video with ambient audio",
                "duration": "4",
                "resolution": "720p",
                "end_user_id": "user-9",
            },
            {
                "Authorization": "Key demo-key",
                "Content-Type": "application/json",
            },
        )
    ]
    assert result["id"] == "seedance-req-123"
    assert result["status"] == "submitted"
    assert result["fal_model_id"] == "/bytedance/seedance-2.0/fast/text-to-video"
    assert result["fal_subpath"] is None


@pytest.mark.asyncio
async def test_fal_adapter_queries_queue_and_returns_completed_video(monkeypatch) -> None:
    adapter = FalAdapter()
    client = _QueueClient(
        [
            _Response(
                {
                    "status": "COMPLETED",
                    "request_id": "fal-req-123",
                    "response_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123",
                    "logs": [{"message": "done"}],
                    "metrics": {"duration": 12.4},
                }
            ),
            _Response(
                {
                    "video": {
                        "url": "https://v3.fal.media/files/video.mp4",
                        "content_type": "video/mp4",
                    },
                    "thumbnail": "https://v3.fal.media/files/thumb.png",
                }
            ),
        ]
    )

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", lambda *args, **kwargs: client)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="veo-3.1-fast",
                execution_model_code="veo-3.1-fast-generate-preview",
                route_group="veo31",
                provider_task_id="fal-req-123",
                result_payload={
                    "status_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123/status",
                    "response_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123",
                    "cancel_url": "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123/cancel",
                },
            ),
            "payload": {},
            "method": "GET",
        }
    )

    assert client.calls == [
        (
            "GET",
            "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123/status",
            None,
            {"Authorization": "Key demo-key"},
        ),
        (
            "GET",
            "https://queue.fal.run/fal-ai/veo3.1/fast/requests/fal-req-123",
            None,
            {"Authorization": "Key demo-key"},
        ),
    ]
    assert result["status"] == "completed"
    assert result["url"] == "https://v3.fal.media/files/video.mp4"
    assert result["logs"] == [{"message": "done"}]
    assert result["metrics"] == {"duration": 12.4}


@pytest.mark.asyncio
async def test_fal_adapter_get_uses_route_group_from_ctx_for_task_entities(monkeypatch) -> None:
    adapter = FalAdapter()
    client = _QueueClient(
        [
            _Response(
                {
                    "status": "COMPLETED",
                    "request_id": "fal-req-task",
                    "response_url": "https://queue.fal.run/fal-ai/veo3.1/requests/fal-req-task",
                    "metrics": {"duration": 8.2},
                }
            ),
            _Response(
                {
                    "video": {
                        "url": "https://v3.fal.media/files/task-video.mp4",
                        "content_type": "video/mp4",
                    }
                }
            ),
        ]
    )

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", lambda *args, **kwargs: client)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="veo-3.1-fast",
                provider_task_id="fal-req-task",
                result_payload={
                    "status_url": "https://queue.fal.run/fal-ai/veo3.1/requests/fal-req-task/status",
                    "response_url": "https://queue.fal.run/fal-ai/veo3.1/requests/fal-req-task",
                    "cancel_url": "https://queue.fal.run/fal-ai/veo3.1/requests/fal-req-task/cancel",
                },
            ),
            "route_group": "veo31",
            "payload": {},
            "method": "GET",
        }
    )

    assert result["status"] == "completed"
    assert result["url"] == "https://v3.fal.media/files/task-video.mp4"
    assert client.calls[0][1].endswith("/status")


@pytest.mark.asyncio
async def test_fal_adapter_get_uses_seedance_route_group_for_task_entities(monkeypatch) -> None:
    adapter = FalAdapter()
    client = _QueueClient(
        [
            _Response(
                {
                    "status": "COMPLETED",
                    "request_id": "seedance-task-req",
                    "response_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-task-req",
                    "metrics": {"duration": 6.4},
                }
            ),
            _Response(
                {
                    "video": {
                        "url": "https://v3.fal.media/files/seedance-video.mp4",
                        "content_type": "video/mp4",
                    }
                }
            ),
        ]
    )

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", lambda *args, **kwargs: client)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="seedance-2.0-fast",
                provider_task_id="seedance-task-req",
                result_payload={
                    "status_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-task-req/status",
                    "response_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-task-req",
                    "cancel_url": "https://queue.fal.run/bytedance/seedance-2.0/fast/text-to-video/requests/seedance-task-req/cancel",
                },
            ),
            "route_group": "seedance",
            "payload": {},
            "method": "GET",
        }
    )

    assert result["status"] == "completed"
    assert result["url"] == "https://v3.fal.media/files/seedance-video.mp4"
    assert client.calls[0][1].endswith("/status")


@pytest.mark.asyncio
async def test_fal_adapter_marks_failed_when_result_endpoint_errors(monkeypatch) -> None:
    adapter = FalAdapter()
    client = _QueueClient(
        [
            _Response(
                {
                    "status": "COMPLETED",
                    "request_id": "fal-req-999",
                    "response_url": "https://queue.fal.run/fal-ai/veo3/requests/fal-req-999",
                }
            ),
            _Response({}, status_code=500, text="upstream render failed"),
        ]
    )

    monkeypatch.setattr("app.domains.platform.providers.fal.httpx.AsyncClient", lambda *args, **kwargs: client)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://fal.run",
                auth_config={"api_key": "demo-key", "queue_base_url": "https://queue.fal.run"},
            ),
            "provider_model": SimpleNamespace(
                public_model_code="veo-3-fast",
                execution_model_code="veo-3-fast",
                route_group="veo3",
                provider_task_id="fal-req-999",
                result_payload={
                    "status_url": "https://queue.fal.run/fal-ai/veo3/requests/fal-req-999/status",
                    "response_url": "https://queue.fal.run/fal-ai/veo3/requests/fal-req-999",
                },
            ),
            "payload": {},
            "method": "GET",
        }
    )

    assert result["status"] == "failed"
    assert "upstream render failed" in result["error"]
