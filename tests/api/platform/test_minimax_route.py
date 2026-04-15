from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, UserAccessContext, require_api_key, require_user_access
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService
from app.domains.platform.services.provider_api_execution import ProviderApiExecutionService


def test_minimax_system_tts_route_uses_system_contract(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_fetch_voice_ids(*, voice_type: str) -> set[str]:
        assert voice_type == "system"
        return {"English_expressive_narrator"}

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        *,
        http_request,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        chain: str | None,
        fallback: bool | None,
        create_invoke_builder,
        response_builder,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, http_request, ctx, create_invoke_builder, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
                "forward_payload": forward_payload,
                "chain": chain,
                "fallback": fallback,
            }
        )
        return response_builder(
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=fixed_model_code,
                created_at=datetime.now(timezone.utc),
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr("app.api.routes.models.minimax._fetch_minimax_voice_ids_for_validation", fake_fetch_voice_ids)
    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "hello",
                "voice_id": "English_expressive_narrator",
                "voice_setting": {"speed": 1},
                "audio_setting": {"format": "mp3"},
                "text_file_id": 123,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "minimax_t2a_async",
        "fixed_model_code": "speech-2.8-hd",
        "payload": {
            "text": "hello",
            "audio_setting": {"format": "mp3"},
            "text_file_id": 123,
            "model": "speech-2.8-hd",
            "voice_setting": {
                "voice_id": "English_expressive_narrator",
                "speed": 1.0,
            },
        },
        "forward_payload": {
            "model": "speech-2.8-hd",
            "text": "hello",
            "voice_id": "English_expressive_narrator",
            "voice_setting": {"speed": 1.0},
            "audio_setting": {"format": "mp3"},
            "text_file_id": 123,
        },
        "chain": "35m",
        "fallback": False,
    }
    assert response.json()["voice_id"] == "English_expressive_narrator"
    assert response.json()["voice_type"] == "system"
    assert response.json()["model"] == "speech-2.8-hd"


def test_minimax_system_tts_route_allows_turbo_model(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_fetch_voice_ids(*, voice_type: str) -> set[str]:
        assert voice_type == "system"
        return {"English_expressive_narrator"}

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        *,
        http_request,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        forward_payload: dict[str, object] | None = None,
        chain: str | None,
        fallback: bool | None,
        create_invoke_builder,
        response_builder,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, http_request, ctx, create_invoke_builder, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
                "forward_payload": forward_payload,
                "chain": chain,
                "fallback": fallback,
            }
        )
        return response_builder(
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=fixed_model_code,
                created_at=datetime.now(timezone.utc),
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr("app.api.routes.models.minimax._fetch_minimax_voice_ids_for_validation", fake_fetch_voice_ids)
    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "speech-2.8-turbo",
                "text": "hello",
                "voice_id": "English_expressive_narrator",
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "minimax_t2a_async",
        "fixed_model_code": "speech-2.8-turbo",
        "payload": {
            "model": "speech-2.8-turbo",
            "text": "hello",
            "voice_setting": {
                "voice_id": "English_expressive_narrator",
            },
        },
        "forward_payload": {
            "model": "speech-2.8-turbo",
            "text": "hello",
            "voice_id": "English_expressive_narrator",
        },
        "chain": "35m",
        "fallback": False,
    }
    assert response.json()["model"] == "speech-2.8-turbo"


def test_minimax_system_tts_route_35m_gateway_skips_local_system_voice_validation(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_fetch_voice_ids(*, voice_type: str) -> set[str]:
        raise AssertionError(f"35m gateway should bypass local voice lookup: {voice_type}")

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        **kwargs,
    ) -> dict[str, object]:
        del self
        return kwargs["response_builder"](
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=kwargs["fixed_model_code"],
                created_at=datetime.now(timezone.utc),
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr("app.api.routes.models.minimax._fetch_minimax_voice_ids_for_validation", fail_fetch_voice_ids)
    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax/system-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "hello",
                "voice_id": "MiniMaxClone1773992276",
            },
        )

    assert response.status_code == 200
    assert response.json()["voice_id"] == "MiniMaxClone1773992276"


def test_minimax_cloned_tts_route_35m_gateway_skips_local_cloned_voice_validation(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    async def fail_fetch_voice_ids(*, voice_type: str) -> set[str]:
        raise AssertionError(f"35m gateway should bypass local voice lookup: {voice_type}")

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        **kwargs,
    ) -> dict[str, object]:
        del self
        return kwargs["response_builder"](
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=kwargs["fixed_model_code"],
                created_at=datetime.now(timezone.utc),
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr("app.api.routes.models.minimax._fetch_minimax_voice_ids_for_validation", fail_fetch_voice_ids)
    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax/cloned-tts",
            headers={"Authorization": "Bearer test-key"},
            json={
                "text": "hello",
                "voice_id": "English_expressive_narrator",
            },
        )

    assert response.status_code == 200
    assert response.json()["voice_id"] == "English_expressive_narrator"


def test_minimax_system_voices_route_supports_catalog_contract(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="api_key",
        api_key_id=3,
        key_name="demo",
    )
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
        persist_request_log: bool = True,
    ) -> dict[str, object]:
        del self, http_request, ctx, provider_code, route_group, model_code, provider_path, method, bill_on_success
        assert payload == {
            "voice_id": "English_expressive_narrator",
            "q": "narrator",
            "page_index": 0,
            "page_size": 20,
        }
        assert forward_payload == payload
        assert persist_request_log is False
        return {
            "items": [
                {
                    "voice_id": "English_expressive_narrator",
                    "voice_name": "Narrator",
                    "description": ["english", "narrator"],
                    "created_time": None,
                },
            ],
            "total": 1,
            "page_index": 0,
            "page_size": 20,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.get(
            "/v1/minimax/system-voices",
            headers={"Authorization": "Bearer test-key"},
            params={"q": "narrator", "voice_id": "English_expressive_narrator"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "voice_id": "English_expressive_narrator",
                "voice_name": "Narrator",
                "description": ["english", "narrator"],
                "created_time": None,
            }
        ],
        "total": 1,
        "page_index": 0,
        "page_size": 20,
    }


def test_minimax_system_voices_route_supports_user_session(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="session",
        session_id="sess_demo",
        session_token="sess_api35_demo",
    )
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
        persist_request_log: bool = True,
    ) -> dict[str, object]:
        del self, http_request, provider_code, route_group, model_code, provider_path, payload, forward_payload, method, bill_on_success
        assert ctx.user_id == 9
        assert persist_request_log is False
        return {
            "items": [
                {
                    "voice_id": "English_expressive_narrator",
                    "voice_name": "Narrator",
                    "description": ["english", "narrator"],
                    "created_time": None,
                }
            ],
            "total": 1,
            "page_index": 0,
            "page_size": 20,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.get(
            "/v1/minimax/system-voices",
            headers={"Authorization": "Bearer sess_api35_demo"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["voice_id"] == "English_expressive_narrator"


def test_minimax_system_voices_route_supports_pagination(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(
        user_id=9,
        auth_mode="api_key",
        api_key_id=3,
        key_name="demo",
    )
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
        persist_request_log: bool = True,
    ) -> dict[str, object]:
        del self, http_request, ctx, provider_code, route_group, model_code, provider_path, method, bill_on_success
        assert payload == {"page_index": 1, "page_size": 1}
        assert forward_payload == payload
        assert persist_request_log is False
        return {
            "items": [
                {"voice_id": "voice_002", "voice_name": "Voice 2", "description": ["two"]},
            ],
            "total": 3,
            "page_index": 1,
            "page_size": 1,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.get(
            "/v1/minimax/system-voices",
            headers={"Authorization": "Bearer test-key"},
            params={"page_index": 1, "page_size": 1},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "voice_id": "voice_002",
                "voice_name": "Voice 2",
                "description": ["two"],
                "created_time": None,
            }
        ],
        "total": 3,
        "page_index": 1,
        "page_size": 1,
    }


def test_minimax_voice_clones_route_supports_catalog_contract(monkeypatch) -> None:
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
        persist_request_log: bool = True,
    ) -> dict[str, object]:
        del self, http_request, ctx, provider_code, route_group, model_code, provider_path, method, bill_on_success
        assert payload == {"page_index": 0, "page_size": 20}
        assert forward_payload == payload
        assert persist_request_log is False
        return {
            "items": [
                {
                    "voice_id": "MiniMaxClone1773992276",
                    "voice_name": "Brand Clone",
                    "description": ["brand"],
                    "created_time": "2026-03-20 12:00:00",
                }
            ],
            "total": 1,
            "page_index": 0,
            "page_size": 20,
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.get(
            "/v1/minimax/voice-clones",
            headers={"Authorization": "Bearer test-key"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "voice_id": "MiniMaxClone1773992276",
                "voice_name": "Brand Clone",
                "description": ["brand"],
                "created_time": "2026-03-20 12:00:00",
            }
        ],
        "total": 1,
        "page_index": 0,
        "page_size": 20,
    }


def test_minimax_voice_clone_route_uses_fixed_model_contract(monkeypatch) -> None:
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
        captured.update(
            {
                "provider_code": provider_code,
                "route_group": route_group,
                "model_code": model_code,
                "provider_path": provider_path,
                "payload": payload,
                "forward_payload": forward_payload,
            }
        )
        return {
            "voice_id": "MiniMaxDemo01",
            "model": "speech-2.8-hd",
            "demo_audio": "https://example.com/demo.mp3",
            "provider_raw": {"ok": True},
        }

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax/voice-clones",
            headers={"Authorization": "Bearer test-key"},
            json={
                "voice_id": "MiniMaxDemo01",
                "audio_url": "https://example.com/source.wav",
                "prompt_audio_url": "https://example.com/prompt.wav",
                "prompt_text": "hello",
            },
        )

    assert response.status_code == 200
    assert captured == {
        "provider_code": "35m",
        "route_group": "minimax_voice_clone",
        "model_code": "speech-2.8-hd",
        "provider_path": "/v1/voice_clone",
        "payload": {
            "voice_id": "MiniMaxDemo01",
            "audio_url": "https://example.com/source.wav",
            "prompt_audio_url": "https://example.com/prompt.wav",
            "prompt_text": "hello",
            "model": "speech-2.8-hd",
        },
        "forward_payload": {
            "voice_id": "MiniMaxDemo01",
            "audio_url": "https://example.com/source.wav",
            "prompt_audio_url": "https://example.com/prompt.wav",
            "prompt_text": "hello",
        },
    }
    assert response.json()["voice_id"] == "MiniMaxDemo01"


def test_minimax_voice_clone_delete_route_uses_platform_contract(monkeypatch) -> None:
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
        captured.update(
            {
                "provider_code": provider_code,
                "route_group": route_group,
                "model_code": model_code,
                "provider_path": provider_path,
                "payload": payload,
                "forward_payload": forward_payload,
            }
        )
        return {"voice_id": "MiniMaxDemo01", "deleted": True}

    monkeypatch.setattr(ProviderApiExecutionService, "execute", fake_execute)

    with TestClient(app) as client:
        response = client.delete(
            "/v1/minimax/voice-clones/MiniMaxDemo01",
            headers={"Authorization": "Bearer test-key"},
        )

    assert response.status_code == 200
    assert captured == {
        "provider_code": "35m",
        "route_group": "minimax_voice_clone",
        "model_code": "speech-2.8-hd",
        "provider_path": "/v1/delete_voice",
        "payload": {"voice_id": "MiniMaxDemo01"},
        "forward_payload": {},
    }
    assert response.json() == {
        "voice_id": "MiniMaxDemo01",
        "deleted": True,
    }
