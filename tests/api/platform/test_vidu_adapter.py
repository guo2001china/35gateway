from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domains.platform.providers.vidu import ViduAdapter


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.content = b"{}"
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.get("base_url")
        self.timeout = kwargs.get("timeout")
        self.calls: list[tuple[str, str, dict | None, dict[str, str] | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, path, json=None, headers=None):
        self.calls.append(("POST", path, json, headers))
        return _Response(
            {
                "task_id": "vidu-task-123",
                "state": "created",
                "model": "viduq3-pro",
            }
        )

    async def get(self, path, headers=None):
        self.calls.append(("GET", path, None, headers))
        return _Response(
            {
                "id": "vidu-task-123",
                "state": "success",
                "credits": 60,
                "creations": [
                    {
                        "id": "creation-1",
                        "url": "https://example.com/video.mp4",
                        "cover_url": "https://example.com/cover.png",
                        "watermarked_url": "https://example.com/video-watermarked.mp4",
                    }
                ],
            }
        )


def test_vidu_adapter_builds_image_request() -> None:
    adapter = ViduAdapter()

    request_payload = adapter.build_request(
        {
            "payload": {
                "model": "viduq3-pro",
                "mode": "image",
                "prompt": "让角色挥手。",
                "images": ["https://example.com/frame.png"],
                "duration": 5,
                "resolution": "720p",
                "audio": True,
                "audio_type": "all",
                "meta_data": {"Label": "demo"},
            }
        }
    )

    assert request_payload == {
        "model": "viduq3-pro",
        "prompt": "让角色挥手。",
        "images": ["https://example.com/frame.png"],
        "duration": 5,
        "resolution": "720p",
        "audio": True,
        "audio_type": "all",
        "meta_data": '{"Label": "demo"}',
    }


@pytest.mark.asyncio
async def test_vidu_adapter_uses_token_auth_for_create(monkeypatch) -> None:
    adapter = ViduAdapter()
    client = _Client()

    monkeypatch.setattr("app.domains.platform.providers.vidu.httpx.AsyncClient", lambda *args, **kwargs: client)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(base_url="https://api.vidu.cn", auth_config={"api_key": "demo-key"}),
            "provider_model": SimpleNamespace(model_code="viduq3-pro"),
            "path": "/ent/v2/img2video",
            "payload": {
                "model": "viduq3-pro",
                "mode": "image",
                "prompt": "让角色挥手。",
                "images": ["https://example.com/frame.png"],
            },
        }
    )

    assert client.calls == [
        (
            "POST",
            "/ent/v2/img2video",
            {
                "model": "viduq3-pro",
                "prompt": "让角色挥手。",
                "images": ["https://example.com/frame.png"],
            },
            {
                "Authorization": "Token demo-key",
                "Content-Type": "application/json",
            },
        )
    ]
    assert result["status"] == "submitted"
    assert result["provider_status"] == "created"


def test_vidu_adapter_parses_query_response() -> None:
    adapter = ViduAdapter()

    result = adapter.parse_response(
        {
            "path": "/ent/v2/tasks/vidu-task-123/creations",
            "provider_model": SimpleNamespace(model_code="viduq3-turbo", provider_task_id="vidu-task-123"),
        },
        {
            "id": "vidu-task-123",
            "state": "success",
            "credits": 35,
            "bgm": False,
            "off_peak": True,
            "creations": [
                {
                    "id": "creation-1",
                    "url": "https://example.com/video.mp4",
                    "cover_url": "https://example.com/cover.png",
                    "watermarked_url": "https://example.com/video-watermarked.mp4",
                }
            ],
        },
    )

    assert result["status"] == "completed"
    assert result["url"] == "https://example.com/video.mp4"
    assert result["watermarked_url"] == "https://example.com/video-watermarked.mp4"
    assert result["credits"] == 35
