from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main_module
from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService
from app.main import create_app


def _patch_lifespan(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "init_app_db", lambda: None)

    async def fake_close_app_db() -> None:
        return None

    monkeypatch.setattr(main_module, "close_app_db", fake_close_app_db)


def test_viduq3_pro_route_uses_vidu_contract(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
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
            {"status": "submitted", "provider_status": "created"},
        )

    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/viduq3-pro",
            headers={"Authorization": "Bearer test-key"},
            json={
                "mode": "image",
                "prompt": "让角色回头看向镜头。",
                "images": ["https://example.com/frame.png"],
                "duration": 5,
                "resolution": "720p",
                "audio": True,
                "off_peak": False,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "vidu",
        "fixed_model_code": "viduq3-pro",
        "payload": {
            "mode": "image",
            "prompt": "让角色回头看向镜头。",
            "images": ["https://example.com/frame.png"],
            "duration": 5,
            "resolution": "720p",
            "audio": True,
            "off_peak": False,
        },
        "chain": None,
        "fallback": None,
    }
    assert response.json()["id"] == "task_demo"
    assert response.json()["provider_task_id"] == "provider_demo"
    assert response.json()["model"] == "viduq3-pro"


def test_viduq3_turbo_route_rejects_wrong_image_count(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/viduq3-turbo",
            headers={"Authorization": "Bearer test-key"},
            json={
                "mode": "start_end",
                "images": ["https://example.com/only-one.png"],
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "two_images_required_for_start_end_mode"


def test_viduq3_pro_rejects_off_peak_without_audio(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/viduq3-pro",
            headers={"Authorization": "Bearer test-key"},
            json={
                "mode": "text",
                "prompt": "一只猫在屋顶上看日落。",
                "off_peak": True,
                "audio": False,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "off_peak_requires_audio_enabled"
