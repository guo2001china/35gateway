from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService


def test_wan26_route_uses_video_contract(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        *,
        http_request,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
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
                "chain": chain,
                "fallback": fallback,
            }
        )
        return response_builder(
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=fixed_model_code,
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "cinematic skyline",
                "input_reference": "https://example.com/frame.png",
                "resolution": "720P",
                "aspect_ratio": "16:9",
                "seconds": 5,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "wan_video",
        "fixed_model_code": "wan2.6",
        "payload": {
            "prompt": "cinematic skyline",
            "input_reference": "https://example.com/frame.png",
            "resolution": "720P",
            "aspect_ratio": "16:9",
            "seconds": 5,
        },
        "chain": None,
        "fallback": None,
    }
    assert response.json()["id"] == "task_demo"
    assert response.json()["provider_task_id"] == "provider_demo"
    assert response.json()["model"] == "wan2.6"


def test_wan26_flash_rejects_text_mode() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6-flash",
            headers={"Authorization": "Bearer test-key"},
            json={"prompt": "text only"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "text_not_supported_for_model"


def test_wan26_rejects_mixed_reference_inputs() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6",
            headers={"Authorization": "Bearer test-key"},
            json={
                "input_reference": "https://example.com/one.png",
                "reference_urls": ["https://example.com/two.png"],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "mixed_reference_inputs_not_allowed"


def test_wan26_rejects_invalid_shot_type() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6",
            headers={"Authorization": "Bearer test-key"},
            json={
                "reference_urls": ["https://example.com/ref-a.png", "https://example.com/ref-b.png"],
                "shot_type": "fixed_camera",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_shot_type"


def test_wan26_rejects_shot_type_outside_reference_mode() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "text only",
                "shot_type": "single",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "shot_type_only_supported_for_reference_mode"


def test_wan26_flash_allows_reference_mode(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_create_task(
        self: AsyncTaskExecutionService,
        *,
        http_request,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        create_invoke_builder,
        response_builder,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, http_request, ctx, chain, fallback, create_invoke_builder, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
            }
        )
        return response_builder(
            SimpleNamespace(
                platform_task_id="task_demo",
                provider_task_id="provider_demo",
                public_model_code=fixed_model_code,
            ),
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/wan2.6-flash",
            headers={"Authorization": "Bearer test-key"},
            json={
                "reference_urls": ["https://example.com/ref-a.png", "https://example.com/ref-b.png"],
                "generate_audio": False,
                "resolution": "1080P",
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "wan_video",
        "fixed_model_code": "wan2.6-flash",
        "payload": {
            "reference_urls": ["https://example.com/ref-a.png", "https://example.com/ref-b.png"],
            "generate_audio": False,
            "resolution": "1080P",
        },
    }
