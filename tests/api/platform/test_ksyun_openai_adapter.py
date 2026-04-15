from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domains.platform.providers.ksyun_openai import KsyunOpenAIAdapter


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "id": "chatcmpl-demo",
            "object": "chat.completion",
            "model": "mgg-9-global",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Here you go.",
                        "audio": {
                            "data": "ZmFrZV9pbWFnZQ==",
                            "extra_content": {
                                "google": {
                                    "mime_type": "image/png",
                                }
                            },
                        },
                    },
                }
            ],
        }


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
        return _Response()


def test_ksyun_openai_adapter_builds_banana_chat_request() -> None:
    adapter = KsyunOpenAIAdapter()

    request_payload = adapter._build_banana_request(
        {
            "provider_model": SimpleNamespace(
                model_code="nano-banana-2",
                public_model_code="nano-banana-2",
                execution_model_code="mgg-9-global",
            ),
            "payload": {
                "prompt": "make a banner",
                "aspect_ratio": "21:9",
                "resolution": "512",
                "image_urls": ["https://example.com/input.png"],
            },
        }
    )

    assert request_payload == {
        "model": "mgg-9-global",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "make a banner\nOutput aspect ratio: 21:9.\nPreferred resolution: 512.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/input.png"},
                    },
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_ksyun_openai_adapter_parses_banana_chat_response(monkeypatch) -> None:
    adapter = KsyunOpenAIAdapter()
    client = _Client()

    def _client_factory(*args, **kwargs):
        return client

    monkeypatch.setattr("app.domains.platform.providers.ksyun_openai.httpx.AsyncClient", _client_factory)

    result = await adapter.invoke(
        {
            "provider": SimpleNamespace(
                base_url="https://global-kspmas.ksyun.com/v1",
                auth_config={"api_key": "demo-key"},
            ),
            "provider_model": SimpleNamespace(
                model_code="nano-banana-2",
                public_model_code="nano-banana-2",
                route_group="banana",
                execution_model_code="mgg-9-global",
            ),
            "path": "/v1beta/models/nano-banana-2:generateContent",
            "payload": {
                "prompt": "make a banner",
                "aspect_ratio": "21:9",
                "resolution": "512",
            },
        }
    )

    assert client.calls == [
        (
            "POST",
            "chat/completions",
            {
                "model": "mgg-9-global",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "make a banner\nOutput aspect ratio: 21:9.\nPreferred resolution: 512.",
                            }
                        ],
                    }
                ],
            },
            {
                "Authorization": "Bearer demo-key",
                "Content-Type": "application/json",
            },
        )
    ]
    assert result["model"] == "nano-banana-2"
    assert result["images"][0]["b64_json"] == "ZmFrZV9pbWFnZQ=="
    assert result["images"][0]["mime_type"] == "image/png"
    assert result["description"] == "Here you go."


def test_ksyun_openai_adapter_strips_think_block_from_description() -> None:
    adapter = KsyunOpenAIAdapter()

    text = adapter._extract_message_text(
        {
            "content": "<think>\ninternal reasoning\n</think>\nFinal visible text.",
        }
    )

    assert text == "Final visible text."
