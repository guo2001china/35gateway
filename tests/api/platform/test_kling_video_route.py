from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main_module
from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService


def _patch_lifespan(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "init_app_db", lambda: None)

    async def fake_close_app_db() -> None:
        return None

    monkeypatch.setattr(main_module, "close_app_db", fake_close_app_db)


def test_kling_o1_route_uses_video_contract(monkeypatch) -> None:
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
            {"status": "submitted", "provider_status": "submitted"},
        )

    monkeypatch.setattr(AsyncTaskExecutionService, "create_task", fake_create_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/kling-o1",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "Make the character wave to camera.",
                "input_reference": "https://example.com/frame.png",
                "mode": "std",
                "aspect_ratio": "16:9",
                "seconds": 5,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "kling_video",
        "fixed_model_code": "kling-o1",
        "payload": {
            "prompt": "Make the character wave to camera.",
            "input_reference": "https://example.com/frame.png",
            "mode": "std",
            "aspect_ratio": "16:9",
            "seconds": 5,
        },
        "chain": None,
        "fallback": None,
    }
    assert response.json()["id"] == "task_demo"
    assert response.json()["provider_task_id"] == "provider_demo"
    assert response.json()["model"] == "kling-o1"


def test_kling_o1_route_rejects_mixed_video_inputs(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/kling-o1",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "extend this shot",
                "video_url": "https://example.com/video.mp4",
                "input_reference": "https://example.com/frame.png",
                "seconds": 5,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "mixed_video_inputs_not_allowed"


def test_kling_o1_route_rejects_last_frame_without_first_frame(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/kling-o1",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "turn this into a cinematic transition",
                "last_frame": "https://example.com/last.png",
                "seconds": 5,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "first_frame_required_for_last_frame"


def test_kling_o1_uses_same_contract_for_reference_images(monkeypatch) -> None:
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
            "/v1/kling-o1",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "Use these references to generate a fashion clip.",
                "reference_images": [
                    "https://example.com/ref-a.png",
                    "https://example.com/ref-b.png",
                ],
                "mode": "pro",
                "seconds": 10,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "kling_video",
        "fixed_model_code": "kling-o1",
        "payload": {
            "prompt": "Use these references to generate a fashion clip.",
            "reference_images": [
                "https://example.com/ref-a.png",
                "https://example.com/ref-b.png",
            ],
            "mode": "pro",
            "seconds": 10,
        },
    }
