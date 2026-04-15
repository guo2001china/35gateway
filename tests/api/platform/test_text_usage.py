from __future__ import annotations

from app.core.pricing.text_usage import estimate_text_usage


def test_estimate_text_usage_ignores_openai_image_urls() -> None:
    usage = estimate_text_usage(
        route_group="openai",
        payload={
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "hello world"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://example.com/a-very-long-image-url-that-should-not-count-at-all.png"
                            },
                        },
                    ],
                }
            ]
        },
    )

    assert usage.input_tokens == 3


def test_estimate_text_usage_ignores_responses_image_inputs() -> None:
    usage = estimate_text_usage(
        route_group="responses",
        payload={
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "hello"},
                        {"type": "input_image", "image_url": "https://example.com/very-long-image.png"},
                    ],
                }
            ],
            "instructions": "system",
        },
    )

    assert usage.input_tokens == 3


def test_estimate_text_usage_ignores_gemini_file_parts() -> None:
    usage = estimate_text_usage(
        route_group="gemini",
        payload={
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "hello"},
                        {
                            "fileData": {
                                "mimeType": "image/png",
                                "fileUri": "https://example.com/very-long-image.png",
                            }
                        },
                    ],
                }
            ]
        },
    )

    assert usage.input_tokens == 2
