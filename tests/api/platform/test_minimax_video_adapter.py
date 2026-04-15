from types import SimpleNamespace

import pytest

from app.domains.platform.providers.minimax import MiniMaxAdapter


def test_minimax_video_adapter_builds_image_request() -> None:
    adapter = MiniMaxAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "MiniMax-Hailuo-2.3",
                "prompt": "cinematic alley",
                "input_reference": "https://example.com/frame.png",
                "resolution": "768P",
                "seconds": 6,
            },
            "route_group": "minimax_video",
        }
    )

    assert payload == {
        "model": "MiniMax-Hailuo-2.3",
        "prompt": "cinematic alley",
        "first_frame_image": "https://example.com/frame.png",
        "resolution": "768P",
        "duration": 6,
    }


def test_minimax_video_adapter_builds_first_last_frame_request() -> None:
    adapter = MiniMaxAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "MiniMax-Hailuo-02",
                "first_frame": "https://example.com/first.png",
                "last_frame": "https://example.com/last.png",
                "aspect_ratio": "16:9",
            },
            "route_group": "minimax_video",
        }
    )

    assert payload == {
        "model": "MiniMax-Hailuo-02",
        "first_frame_image": "https://example.com/first.png",
        "last_frame_image": "https://example.com/last.png",
        "aspect_ratio": "16:9",
    }


def test_minimax_video_adapter_parses_create_response() -> None:
    adapter = MiniMaxAdapter()

    response = adapter.parse_response(
        {
            "route_group": "minimax_video",
            "path": "/v1/video_generation",
            "payload": {"model": "MiniMax-Hailuo-2.3", "seconds": 6, "resolution": "768P"},
        },
        {"task_id": "12345", "base_resp": {"status_code": 0}},
    )

    assert response["id"] == "12345"
    assert response["status"] == "submitted"
    assert response["model"] == "MiniMax-Hailuo-2.3"
    assert response["seconds"] == "6"
    assert response["size"] == "768P"


def test_minimax_video_adapter_parses_query_response() -> None:
    adapter = MiniMaxAdapter()

    response = adapter.parse_response(
        {
            "route_group": "minimax_video",
            "path": "/v1/query/video_generation?task_id=12345",
            "provider_model": SimpleNamespace(model_code="MiniMax-Hailuo-02"),
        },
        {
            "task_id": "12345",
            "status": "Success",
            "file_id": "67890",
            "video_width": 1280,
            "video_height": 720,
            "base_resp": {"status_code": 0},
        },
    )

    assert response == {
        "id": "12345",
        "object": "video",
        "status": "completed",
        "provider_status": "success",
        "file_id": "67890",
        "model": "MiniMax-Hailuo-02",
        "size": "1280x720",
        "provider_raw": {
            "task_id": "12345",
            "status": "Success",
            "file_id": "67890",
            "video_width": 1280,
            "video_height": 720,
            "base_resp": {"status_code": 0},
        },
    }


@pytest.mark.asyncio
async def test_minimax_video_adapter_get_query_does_not_build_create_payload(monkeypatch) -> None:
    adapter = MiniMaxAdapter()

    def fail_build_request(ctx):
        raise AssertionError(f"build_request should not be called for GET: {ctx}")

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"task_id":"12345","status":"Preparing","base_resp":{"status_code":0}}'

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"task_id": "12345", "status": "Preparing", "base_resp": {"status_code": 0}}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def get(self, path, headers=None, params=None):
            assert path == "/v1/query/video_generation"
            assert params == {"task_id": "12345"}
            assert headers == {"Authorization": "Bearer demo-key"}
            return _FakeResponse()

    monkeypatch.setattr(adapter, "build_request", fail_build_request)
    monkeypatch.setattr("app.domains.platform.providers.minimax.httpx.AsyncClient", _FakeAsyncClient)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(base_url="https://api.minimaxi.com", auth_config={"api_key": "demo-key"}),
            "provider_model": SimpleNamespace(model_code="MiniMax-Hailuo-2.3"),
            "route_group": "minimax_video",
            "path": "/v1/query/video_generation?task_id=12345",
            "method": "GET",
        }
    )

    assert result["status"] == "submitted"
    assert result["provider_status"] == "preparing"
