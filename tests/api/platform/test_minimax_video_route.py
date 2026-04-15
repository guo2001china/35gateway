from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService


def test_minimax_hailuo_23_route_uses_video_contract(monkeypatch) -> None:
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
            "/v1/minimax-hailuo-2.3",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "cinematic alley",
                "input_reference": "https://example.com/frame.png",
                "resolution": "768P",
                "aspect_ratio": "16:9",
                "seconds": 6,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "minimax_video",
        "fixed_model_code": "minimax-hailuo-2.3",
        "payload": {
            "prompt": "cinematic alley",
            "input_reference": "https://example.com/frame.png",
            "resolution": "768P",
            "aspect_ratio": "16:9",
            "seconds": 6,
        },
        "chain": None,
        "fallback": None,
    }
    assert response.json()["id"] == "task_demo"
    assert response.json()["provider_task_id"] == "provider_demo"
    assert response.json()["model"] == "minimax-hailuo-2.3"


def test_minimax_hailuo_23_fast_requires_image() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax-hailuo-2.3-fast",
            headers={"Authorization": "Bearer test-key"},
            json={"prompt": "text-only video"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "image_required_for_model"


def test_minimax_hailuo_23_rejects_first_last_frame_mode() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/minimax-hailuo-2.3",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "transition",
                "first_frame": "https://example.com/first.png",
                "last_frame": "https://example.com/last.png",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "first_last_frame_not_supported"


def test_minimax_hailuo_02_allows_first_last_frame_mode(monkeypatch) -> None:
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
            "/v1/minimax-hailuo-02",
            headers={"Authorization": "Bearer test-key"},
            json={
                "first_frame": "https://example.com/first.png",
                "last_frame": "https://example.com/last.png",
                "resolution": "512P",
                "seconds": 6,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "minimax_video",
        "fixed_model_code": "minimax-hailuo-02",
        "payload": {
            "first_frame": "https://example.com/first.png",
            "last_frame": "https://example.com/last.png",
            "resolution": "512P",
            "seconds": 6,
        },
    }
