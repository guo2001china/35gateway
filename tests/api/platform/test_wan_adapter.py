from types import SimpleNamespace

import pytest

from app.domains.platform.providers.wan import WanAdapter


def test_wan_adapter_builds_image_request_for_flash() -> None:
    adapter = WanAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "wan2.6-flash",
                "prompt": "clean product ad",
                "input_reference": "https://example.com/frame.png",
                "resolution": "1080P",
                "aspect_ratio": "16:9",
                "seconds": 5,
                "generate_audio": False,
            },
            "route_group": "wan_video",
        }
    )

    assert payload == {
        "model": "wan2.6-i2v-flash",
        "input": {
            "prompt": "clean product ad",
            "img_url": "https://example.com/frame.png",
        },
        "parameters": {
            "size": "1920*1080",
            "duration": 5,
            "audio": False,
        },
    }


def test_wan_adapter_builds_reference_request() -> None:
    adapter = WanAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "wan2.6",
                "reference_urls": ["https://example.com/a.png", "https://example.com/b.png"],
                "shot_type": "single",
            },
            "route_group": "wan_video",
        }
    )

    assert payload == {
        "model": "wan2.6-r2v",
        "input": {
            "reference_urls": ["https://example.com/a.png", "https://example.com/b.png"],
        },
        "parameters": {
            "size": "1280*720",
            "shot_type": "single",
        },
    }


def test_wan_adapter_parses_create_response() -> None:
    adapter = WanAdapter()

    response = adapter.parse_response(
        {
            "route_group": "wan_video",
            "path": "/api/v1/services/aigc/video-generation/video-synthesis",
            "payload": {"model": "wan2.6", "seconds": 5, "resolution": "720P"},
        },
        {"output": {"task_id": "task-123"}},
    )

    assert response["id"] == "task-123"
    assert response["status"] == "submitted"
    assert response["model"] == "wan2.6"
    assert response["resolved_model"] == "wan2.6-t2v"
    assert response["seconds"] == "5"
    assert response["size"] == "1280*720"


def test_wan_adapter_parses_query_response() -> None:
    adapter = WanAdapter()

    response = adapter.parse_response(
        {
            "route_group": "wan_video",
            "path": "/api/v1/tasks/task-123",
            "provider_model": SimpleNamespace(model_code="wan2.6-flash", result_payload={"resolved_model": "wan2.6-r2v-flash"}),
        },
        {
            "output": {
                "task_id": "task-123",
                "task_status": "SUCCEEDED",
                "video_url": "https://example.com/video.mp4",
            },
            "usage": {
                "duration": 5,
                "video_ratio": "1920*1080",
            },
        },
    )

    assert response == {
        "id": "task-123",
        "object": "video",
        "status": "completed",
        "provider_status": "succeeded",
        "model": "wan2.6-flash",
        "resolved_model": "wan2.6-r2v-flash",
        "seconds": "5",
        "size": "1920*1080",
        "url": "https://example.com/video.mp4",
        "provider_raw": {
            "output": {
                "task_id": "task-123",
                "task_status": "SUCCEEDED",
                "video_url": "https://example.com/video.mp4",
            },
            "usage": {
                "duration": 5,
                "video_ratio": "1920*1080",
            },
        },
    }


@pytest.mark.asyncio
async def test_wan_adapter_get_query_does_not_build_create_payload(monkeypatch) -> None:
    adapter = WanAdapter()

    def fail_build_request(ctx):
        raise AssertionError(f"build_request should not be called for GET: {ctx}")

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"output":{"task_id":"task-123","task_status":"RUNNING"}}'

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"output": {"task_id": "task-123", "task_status": "RUNNING"}}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def get(self, path, headers=None):
            assert path == "/api/v1/tasks/task-123"
            assert headers == {"Authorization": "Bearer demo-key"}
            return _FakeResponse()

    monkeypatch.setattr(adapter, "build_request", fail_build_request)
    monkeypatch.setattr("app.domains.platform.providers.wan.httpx.AsyncClient", _FakeAsyncClient)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(base_url="https://dashscope.aliyuncs.com", auth_config={"api_key": "demo-key"}),
            "provider_model": SimpleNamespace(model_code="wan2.6"),
            "route_group": "wan_video",
            "path": "/api/v1/tasks/task-123",
            "method": "GET",
        }
    )

    assert result["status"] == "processing"
    assert result["provider_status"] == "running"
