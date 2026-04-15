from __future__ import annotations

import httpx

import pytest
from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, UserAccessContext, require_api_key, require_user_access
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.provider_api_execution import ProviderApiExecutionService


def test_qwen_system_tts_route_allows_standard_mode(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_execute(
        self: ProviderApiExecutionService,
        *,
        http_request,
        ctx,
        provider_code: str,
        route_group: str,
        model_code: str,
        provider_path: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        method: str = "POST",
        bill_on_success: bool = False,
    ) -> dict[str, object]:
        del self, http_request, ctx, method
        captured.update(
            {
                "provider_code": provider_code,
                "route_group": route_group,
                "model_code": model_code,
                "provider_path": provider_path,
                "payload": payload,
                "forward_payload": forward_payload,
                "bill_on_success": bill_on_success,
            }
        )
        return {
            "request_id": "req_qwen_tts",
            "voice": "Cherry",
            "mode": "standard",
            "output": {"finish_reason": "stop"},
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "Cherry",
                "mode": "standard",
            },
        )

    assert response.status_code == 200
    assert captured["provider_code"] == "35m"
    assert captured["model_code"] == "qwen3-tts-flash"
    assert captured["route_group"] == "qwen_tts"
    assert captured["bill_on_success"] is True
    assert captured["payload"] == {
        "model": "qwen3-tts-flash",
        "input": {
            "text": "欢迎来到 film35。",
            "voice": "Cherry",
        },
    }
    assert captured["forward_payload"] == {
        "text": "欢迎来到 film35。",
        "voice": "Cherry",
        "mode": "standard",
    }
    assert response.json()["voice"] == "Cherry"
    assert response.json()["mode"] == "standard"


def test_qwen_system_tts_route_rejects_standard_mode_instructions(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute should not be called")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fail_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "Cherry",
                "mode": "standard",
                "instructions": "请以新闻播报风格朗读。",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "instructions_not_allowed"


def test_qwen_system_tts_route_rejects_non_system_voice(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute should not be called")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fail_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "brand_voice",
                "mode": "standard",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "system_voice_required"


def test_qwen_system_tts_route_rejects_unknown_system_voice(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute should not be called")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fail_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "UnknownVoice",
                "mode": "standard",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "system_voice_required"


def test_qwen_system_tts_route_rejects_invalid_mode(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute should not be called")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fail_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "Cherry",
                "mode": "narration",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_mode"


def test_qwen_cloned_tts_route_rejects_instructions(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_execute(*args, **kwargs):
        raise AssertionError("execute should not be called")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fail_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/cloned-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "brand_voice",
                "optimize_instructions": True,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "instructions_not_allowed"


def test_qwen_cloned_tts_route_35m_gateway_skips_local_voice_membership_check(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fake_execute(
        self: ProviderApiExecutionService,
        *,
        http_request,
        ctx,
        provider_code: str,
        route_group: str,
        model_code: str,
        provider_path: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        method: str = "POST",
        bill_on_success: bool = False,
    ) -> dict[str, object]:
        del self, http_request, ctx, method, bill_on_success
        assert provider_code == "35m"
        assert route_group == "qwen_tts"
        assert model_code == "qwen3-tts-vc-2026-01-22"
        assert provider_path == "/api/v1/services/aigc/multimodal-generation/generation"
        assert payload == {
            "model": "qwen3-tts-vc-2026-01-22",
            "input": {
                "text": "欢迎来到 film35。",
                "voice": "missing_voice",
            },
        }
        assert forward_payload == {
            "text": "欢迎来到 film35。",
            "voice": "missing_voice",
        }
        return {
            "request_id": "req_qwen_tts",
            "voice": "missing_voice",
            "output": {"finish_reason": "stop"},
        }

    async def fail_fetch_cloned_voice_names() -> set[str]:
        raise AssertionError("35m gateway should bypass local cloned voice membership lookup")

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)
    monkeypatch.setattr(
        "app.api.routes.models.qwen._fetch_qwen_cloned_voice_names_for_validation",
        fail_fetch_cloned_voice_names,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/cloned-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "欢迎来到 film35。",
                "voice": "missing_voice",
            },
        )

    assert response.status_code == 200
    assert response.json()["voice"] == "missing_voice"


@pytest.mark.asyncio
async def test_fetch_qwen_cloned_voice_names_retries_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes.models import qwen as qwen_route

    class _Provider:
        adapter_key = "qwen"

    class _Adapter:
        def __init__(self) -> None:
            self.calls = 0

        async def invoke(self, ctx):  # noqa: ANN001
            del ctx
            self.calls += 1
            if self.calls == 1:
                raise httpx.ConnectError("temporary lookup failure")
            return {"output": {"voice_list": [{"voice": "brand_voice_001"}]}}

    adapter = _Adapter()
    monkeypatch.setattr(qwen_route, "get_provider", lambda _code: _Provider())
    monkeypatch.setattr(qwen_route, "get_adapter", lambda _key: adapter)

    result = await qwen_route._fetch_qwen_cloned_voice_names_for_validation()

    assert result == {"brand_voice_001"}
    assert adapter.calls == 2


@pytest.mark.asyncio
async def test_fetch_qwen_cloned_voice_names_paginates_with_small_page_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routes.models import qwen as qwen_route

    class _Provider:
        adapter_key = "qwen"

    captured_payloads: list[dict[str, object]] = []

    class _Adapter:
        async def invoke(self, ctx):  # noqa: ANN001
            captured_payloads.append(dict(ctx["payload"]))
            page_index = ctx["payload"]["input"]["page_index"]
            if page_index == 0:
                return {
                    "output": {
                        "voice_list": [
                            {"voice": f"voice_{index:03d}"}
                            for index in range(qwen_route.QWEN_CLONED_VOICE_VALIDATION_PAGE_SIZE)
                        ]
                    }
                }
            return {"output": {"voice_list": [{"voice": "voice_tail"}]}}

    monkeypatch.setattr(qwen_route, "get_provider", lambda _code: _Provider())
    monkeypatch.setattr(qwen_route, "get_adapter", lambda _key: _Adapter())

    result = await qwen_route._fetch_qwen_cloned_voice_names_for_validation()

    assert "voice_000" in result
    assert "voice_tail" in result
    assert len(captured_payloads) == 2
    assert captured_payloads[0]["input"]["page_size"] == qwen_route.QWEN_CLONED_VOICE_VALIDATION_PAGE_SIZE
    assert captured_payloads[0]["input"]["page_index"] == 0
    assert captured_payloads[1]["input"]["page_index"] == 1


def test_qwen_system_voices_route_supports_filters() -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="api_key",
        api_key_id=3,
        key_name="demo",
    )

    with TestClient(app) as client:
        response = client.get(
            "/v1/qwen/system-voices",
            headers={"Authorization": "Bearer test-key"},
            params={"language": "zh", "mode": "instruct", "voice": "Cherry"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page_index"] == 0
    assert payload["page_size"] == 20
    assert payload["items"][0]["voice"] == "Cherry"
    assert "zh" in payload["items"][0]["languages"]
    assert payload["items"][0]["modes"] == ["standard", "instruct"]


def test_qwen_system_voices_route_supports_user_session() -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="session",
        session_id="sess_demo",
        session_token="sess_api35_demo",
    )

    with TestClient(app) as client:
        response = client.get(
            "/v1/qwen/system-voices",
            headers={"Authorization": "Bearer sess_api35_demo"},
            params={"voice": "Cherry"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["voice"] == "Cherry"


def test_qwen_system_voices_route_returns_full_published_catalog() -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="api_key",
        api_key_id=3,
        key_name="demo",
    )

    with TestClient(app) as client:
        response = client.get(
            "/v1/qwen/system-voices",
            headers={"Authorization": "Bearer test-key"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 31
    assert payload["page_index"] == 0
    assert payload["page_size"] == 20
    assert len(payload["items"]) == 20
    returned_voices = [item["voice"] for item in payload["items"]]
    assert returned_voices[:5] == ["Cherry", "Serena", "Ethan", "Chelsie", "Callie"]
    assert "Diana" in returned_voices


def test_qwen_system_voices_route_supports_pagination() -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="api_key",
        api_key_id=3,
        key_name="demo",
    )

    with TestClient(app) as client:
        response = client.get(
            "/v1/qwen/system-voices",
            headers={"Authorization": "Bearer test-key"},
            params={"page_index": 1, "page_size": 5},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 31
    assert payload["page_index"] == 1
    assert payload["page_size"] == 5
    assert [item["voice"] for item in payload["items"]] == [
        "Merry",
        "Kangkang",
        "Junyang",
        "Enya",
        "Canna",
    ]


def test_qwen_voice_clones_route_uses_name_contract(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_execute(
        self: ProviderApiExecutionService,
        *,
        http_request,
        ctx,
        provider_code: str,
        route_group: str,
        model_code: str,
        provider_path: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        method: str = "POST",
        bill_on_success: bool = False,
    ) -> dict[str, object]:
        del self, http_request, ctx, method, bill_on_success
        captured["provider_code"] = provider_code
        captured["forward_payload"] = forward_payload
        captured["payload"] = payload
        return {
            "request_id": "req_clone",
            "voice": "brand_voice_001",
            "name": "brand_voice",
            "usage": None,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/qwen/voice-clones",
            headers={"Authorization": "Bearer test-key"},
            json={
                "name": "brand_voice",
                "audio_url": "https://example.com/brand-voice.wav",
                "language": "zh",
            },
        )

    assert response.status_code == 200
    assert captured["provider_code"] == "35m"
    assert captured["payload"] == {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": "qwen3-tts-vc-2026-01-22",
            "preferred_name": "brand_voice",
            "audio": {"data": "https://example.com/brand-voice.wav"},
            "language": "zh",
        },
    }
    assert captured["forward_payload"] == {
        "name": "brand_voice",
        "audio_url": "https://example.com/brand-voice.wav",
        "language": "zh",
    }
    assert response.json() == {
        "request_id": "req_clone",
        "voice": "brand_voice_001",
        "name": "brand_voice",
        "usage": None,
    }


def test_qwen_voice_clones_list_skips_request_log_persistence(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_execute(
        self: ProviderApiExecutionService,
        *,
        http_request,
        ctx,
        provider_code: str,
        route_group: str,
        model_code: str,
        provider_path: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        method: str = "POST",
        bill_on_success: bool = False,
        persist_request_log: bool = True,
    ) -> dict[str, object]:
        del self, http_request, ctx, provider_code, route_group, model_code, provider_path, method, bill_on_success
        captured["payload"] = payload
        captured["forward_payload"] = forward_payload
        captured["persist_request_log"] = persist_request_log
        return {
            "request_id": "req_qwen_voice_list",
            "items": [
                {
                    "voice": "brand_voice_001",
                    "gmt_create": "2026-04-10 10:00:00",
                }
            ],
            "page_index": 0,
            "page_size": 10,
            "usage": None,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.get(
            "/v1/qwen/voice-clones",
            headers={"Authorization": "Bearer test-key"},
            params={"page_index": 0, "page_size": 10},
        )

    assert response.status_code == 200
    assert captured["persist_request_log"] is False
    assert captured["payload"] == {
        "page_index": 0,
        "page_size": 10,
    }
    assert captured["forward_payload"] == {
        "page_index": 0,
        "page_size": 10,
    }
    assert response.json() == {
        "request_id": "req_qwen_voice_list",
        "items": [
            {
                "voice": "brand_voice_001",
                "gmt_create": "2026-04-10 10:00:00",
            }
        ],
        "page_index": 0,
        "page_size": 10,
        "usage": None,
    }
