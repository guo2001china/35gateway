from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.main import create_app


def test_nano_banana_estimate_uses_public_model_code(monkeypatch) -> None:
    from app.api.routes.models import banana as banana_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_execute_proxy_request(*, http_request, ctx, db, route_group, requested_model, provider_path, payload, chain, allow_fallback):
        del http_request, ctx, db, chain, allow_fallback
        captured.update(
            {
                "route_group": route_group,
                "requested_model": requested_model,
                "provider_path": provider_path,
                "payload": payload,
            }
        )
        return {"data": [{"url": "https://example.com/image.png"}]}

    monkeypatch.setattr(banana_route, "execute_proxy_request", fake_execute_proxy_request)

    with TestClient(app) as client:
        response = client.post(
            "/v1/nano-banana",
            headers={"Authorization": "Bearer test-key"},
            json={"prompt": "draw a red apple"},
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "banana",
        "requested_model": "nano-banana",
        "provider_path": "/v1beta/models/nano-banana:generateContent",
        "payload": {"prompt": "draw a red apple"},
    }


def test_nano_banana_2_execute_uses_public_model_code(monkeypatch) -> None:
    from app.api.routes.models import banana as banana_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    async def fake_execute_proxy_request(*, http_request, ctx, db, route_group, requested_model, provider_path, payload, chain, allow_fallback):
        del http_request, ctx, db, chain, allow_fallback
        captured.update(
            {
                "route_group": route_group,
                "requested_model": requested_model,
                "provider_path": provider_path,
                "payload": payload,
            }
        )
        return {"data": [{"url": "https://example.com/image.png"}]}

    monkeypatch.setattr(banana_route, "execute_proxy_request", fake_execute_proxy_request)

    with TestClient(app) as client:
        response = client.post(
            "/v1/nano-banana-2",
            headers={"Authorization": "Bearer test-key"},
            json={"prompt": "draw a blue apple"},
        )

    assert response.status_code == 200
    assert captured == {
        "route_group": "banana",
        "requested_model": "nano-banana-2",
        "provider_path": "/v1beta/models/nano-banana-2:generateContent",
        "payload": {"prompt": "draw a blue apple"},
    }


def test_nano_banana_rejects_provider_specific_extra_fields() -> None:
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    with TestClient(app) as client:
        response = client.post(
            "/v1/nano-banana-2",
            headers={"Authorization": "Bearer test-key"},
            json={
                "prompt": "draw a blue apple",
                "output_format": "png",
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "output_format"] for item in detail)
