from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService
from app.main import create_app


def test_seedance20_fast_route_uses_public_model_code(monkeypatch) -> None:
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
            "/v1/seedance-2.0-fast",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "cinematic product teaser with synced sound",
                "resolution": "720p",
                "seconds": 4,
            },
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "seedance",
        "fixed_model_code": "seedance-2.0-fast",
        "payload": {
            "prompt": "cinematic product teaser with synced sound",
            "resolution": "720p",
            "seconds": 4,
        },
        "chain": None,
        "fallback": None,
    }
    assert response.json()["model"] == "seedance-2.0-fast"


def test_seedance_route_rejects_seconds_out_of_range() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/seedance-2.0",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "too long request",
                "seconds": 16,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "seconds_out_of_range"
