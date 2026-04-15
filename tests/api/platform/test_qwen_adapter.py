from types import SimpleNamespace

from app.domains.platform.providers.qwen import QwenAdapter


def test_qwen_adapter_uses_provider_upstream_model_alias() -> None:
    adapter = QwenAdapter()

    payload = adapter.build_request(
        {
            "payload": {"model": "qwen3-tts-flash", "input": {"text": "hi", "voice": "Diana"}},
            "provider_model": SimpleNamespace(execution_model_code="qwen-tts-flash"),
        }
    )

    assert payload["model"] == "qwen-tts-flash"


def test_qwen_adapter_preserves_public_model_and_provider_model() -> None:
    adapter = QwenAdapter()

    response = adapter.parse_response(
        {
            "payload": {"model": "qwen3-tts-instruct-flash"},
            "path": "/api/v1/services/aigc/multimodal-generation/generation",
        },
        {"model": "qwen-tts-flash-instruct", "output": {"finish_reason": "stop"}},
    )

    assert response["model"] == "qwen3-tts-instruct-flash"
    assert response["provider_model"] == "qwen-tts-flash-instruct"
