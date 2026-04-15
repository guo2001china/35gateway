from __future__ import annotations

import pytest

from app.domains.platform.providers.google import GoogleAdapter


class _ProviderModel:
    def __init__(self, model_code: str, execution_model_code: str | None = None) -> None:
        self.model_code = model_code
        self.public_model_code = model_code
        self.execution_model_code = execution_model_code


@pytest.mark.asyncio
async def test_google_banana_request_keeps_512_for_nano_banana_2() -> None:
    adapter = GoogleAdapter()

    payload = await adapter._build_banana_request(
        {
            "payload": {
                "prompt": "make a banner",
                "aspect_ratio": "21:9",
                "resolution": "512",
            },
            "provider_model": _ProviderModel("gemini-3.1-flash-image-preview"),
        }
    )

    assert payload["generationConfig"]["imageConfig"] == {
        "aspectRatio": "21:9",
        "imageSize": "512",
    }


@pytest.mark.asyncio
async def test_google_banana_request_omits_image_size_for_nano_banana_base() -> None:
    adapter = GoogleAdapter()

    payload = await adapter._build_banana_request(
        {
            "payload": {
                "prompt": "make a poster",
                "aspect_ratio": "16:9",
                "resolution": "1K",
            },
            "provider_model": _ProviderModel("gemini-2.5-flash-image"),
        }
    )

    assert payload["generationConfig"]["imageConfig"] == {
        "aspectRatio": "16:9",
    }


def test_google_banana_path_uses_execution_model_code() -> None:
    adapter = GoogleAdapter()

    path = adapter._resolve_model_path(
        {
            "provider_model": _ProviderModel(
                "nano-banana",
                execution_model_code="gemini-2.5-flash-image",
            )
        },
        "/v1beta/models/nano-banana:generateContent",
    )

    assert path == "/v1beta/models/gemini-2.5-flash-image:generateContent"
