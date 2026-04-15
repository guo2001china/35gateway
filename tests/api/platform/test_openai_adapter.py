from types import SimpleNamespace

from app.domains.platform.providers.openai import OpenAIAdapter, _normalize_request_path


def test_openai_adapter_uses_provider_upstream_model_alias() -> None:
    adapter = OpenAIAdapter()

    payload = adapter.build_request(
        {
            "payload": {"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "hi"}]},
            "provider_model": SimpleNamespace(execution_model_code="google/gemini-2.5-flash"),
        }
    )

    assert payload["model"] == "google/gemini-2.5-flash"


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "id": "chatcmpl_test",
            "object": "chat.completion",
            "model": "qwen/qwen3-coder:free",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }


class _Client:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, path, json=None, headers=None):
        return _Response()


def test_openai_adapter_preserves_upstream_model_as_provider_model(monkeypatch) -> None:
    adapter = OpenAIAdapter()
    monkeypatch.setattr("app.domains.platform.providers.openai.httpx.AsyncClient", _Client)

    import asyncio

    result = asyncio.run(
        adapter.invoke(
            {
                "provider": SimpleNamespace(base_url="https://openrouter.ai/api/v1", auth_config={"api_key": "k"}),
                "provider_model": SimpleNamespace(execution_model_code="openrouter/free"),
                "path": "/v1/chat/completions",
                "payload": {"model": "openrouter-free", "messages": [{"role": "user", "content": "hi"}]},
            }
        )
    )

    assert result["model"] == "openrouter-free"
    assert result["provider_model"] == "qwen/qwen3-coder:free"


def test_openai_adapter_normalizes_path_for_versioned_base_url() -> None:
    assert _normalize_request_path(
        base_url="https://openrouter.ai/api/v1",
        path="/v1/chat/completions",
    ) == "chat/completions"
