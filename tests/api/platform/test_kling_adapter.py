from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest

from app.domains.platform.providers.kling import KlingAdapter, _build_authorization_header


def test_kling_adapter_builds_reference_image_request() -> None:
    adapter = KlingAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "kling-o1",
                "prompt": "Make this look like a premium ad.",
                "reference_images": [
                    "https://example.com/ref-a.png",
                    "https://example.com/ref-b.png",
                ],
                "mode": "std",
                "seconds": 10,
                "aspect_ratio": "16:9",
            },
            "route_group": "kling_video",
        }
    )

    assert payload == {
        "model_name": "kling-video-o1",
        "prompt": "Make this look like a premium ad.",
        "duration": "10",
        "mode": "std",
        "sound": "off",
        "aspect_ratio": "16:9",
        "image_list": [
            {"image_url": "https://example.com/ref-a.png"},
            {"image_url": "https://example.com/ref-b.png"},
        ],
    }


def test_kling_adapter_builds_video_reference_request() -> None:
    adapter = KlingAdapter()

    payload = adapter.build_request(
        {
            "payload": {
                "model": "kling-o1",
                "prompt": "Use this clip as motion reference for a sequel shot.",
                "video_url": "https://example.com/reference.mp4",
                "seconds": 5,
            },
            "route_group": "kling_video",
        }
    )

    assert payload == {
        "model_name": "kling-video-o1",
        "prompt": "Use this clip as motion reference for a sequel shot.",
        "duration": "5",
        "mode": "pro",
        "sound": "off",
        "video_list": [
            {
                "video_url": "https://example.com/reference.mp4",
                "refer_type": "feature",
                "keep_original_sound": "no",
            }
        ],
    }


def test_kling_adapter_parses_create_response() -> None:
    adapter = KlingAdapter()

    response = adapter.parse_response(
        {
            "route_group": "kling_video",
            "path": "/v1/videos/omni-video",
            "payload": {"model": "kling-o1", "seconds": 5},
        },
        {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "task_status": "submitted",
                "created_at": 1774436400000,
            },
        },
    )

    assert response == {
        "id": "task-123",
        "object": "video",
        "status": "submitted",
        "provider_status": "submitted",
        "model": "kling-o1",
        "resolved_model": "kling-video-o1",
        "created_at": 1774436400,
        "seconds": "5",
        "provider_raw": {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "task_status": "submitted",
                "created_at": 1774436400000,
            },
        },
    }


def test_kling_adapter_parses_query_response() -> None:
    adapter = KlingAdapter()

    response = adapter.parse_response(
        {
            "route_group": "kling_video",
            "path": "/v1/videos/omni-video/task-123",
            "provider_model": SimpleNamespace(model_code="kling-o1", result_payload={"resolved_model": "kling-video-o1"}),
        },
        {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "task_status": "succeed",
                "created_at": 1774436400000,
                "task_result": {
                    "videos": [
                        {
                            "id": "video-123",
                            "url": "https://example.com/video.mp4",
                            "watermark_url": "https://example.com/video-watermark.mp4",
                            "duration": "5",
                        }
                    ]
                },
            },
        },
    )

    assert response == {
        "id": "task-123",
        "object": "video",
        "status": "completed",
        "provider_status": "succeed",
        "model": "kling-o1",
        "resolved_model": "kling-video-o1",
        "created_at": 1774436400,
        "seconds": "5",
        "url": "https://example.com/video.mp4",
        "video": {
            "id": "video-123",
            "url": "https://example.com/video.mp4",
            "watermark_url": "https://example.com/video-watermark.mp4",
            "duration": "5",
        },
        "error": None,
        "provider_raw": {
            "code": 0,
            "data": {
                "task_id": "task-123",
                "task_status": "succeed",
                "created_at": 1774436400000,
                "task_result": {
                    "videos": [
                        {
                            "id": "video-123",
                            "url": "https://example.com/video.mp4",
                            "watermark_url": "https://example.com/video-watermark.mp4",
                            "duration": "5",
                        }
                    ]
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_kling_adapter_get_query_does_not_build_create_payload(monkeypatch) -> None:
    adapter = KlingAdapter()

    def fail_build_request(ctx):
        raise AssertionError(f"build_request should not be called for GET: {ctx}")

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"code":0,"data":{"task_id":"task-123","task_status":"processing"}}'

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"code": 0, "data": {"task_id": "task-123", "task_status": "processing"}}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def get(self, path, headers=None):
            assert path == "/v1/videos/omni-video/task-123"
            assert headers == {"Authorization": "Bearer demo-key"}
            return _FakeResponse()

    monkeypatch.setattr(adapter, "build_request", fail_build_request)
    monkeypatch.setattr("app.domains.platform.providers.kling.httpx.AsyncClient", _FakeAsyncClient)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(base_url="https://api-singapore.klingai.com", auth_config={"api_key": "demo-key"}),
            "provider_model": SimpleNamespace(model_code="kling-o1"),
            "route_group": "kling_video",
            "path": "/v1/videos/omni-video/task-123",
            "method": "GET",
        }
    )

    assert result["status"] == "processing"
    assert result["provider_status"] == "processing"


def test_kling_adapter_builds_jwt_authorization_header() -> None:
    header = _build_authorization_header(
        {
            "access_key": "demo-ak",
            "secret_key": "demo-sk",
        }
    )

    assert header.startswith("Bearer ")
    token = header.removeprefix("Bearer ")
    encoded_header, encoded_payload, encoded_signature = token.split(".")
    assert encoded_signature

    decoded_header = json.loads(base64.urlsafe_b64decode(encoded_header + "==").decode())
    decoded_payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "==").decode())

    assert decoded_header == {"alg": "HS256", "typ": "JWT"}
    assert decoded_payload["iss"] == "demo-ak"
    assert isinstance(decoded_payload["nbf"], int)
    assert isinstance(decoded_payload["exp"], int)
    assert decoded_payload["exp"] > decoded_payload["nbf"]
