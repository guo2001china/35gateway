from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.auth_sessions import SessionAuthService


def _patch_lifespan(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "init_app_db", lambda: None)

    async def fake_close_app_db() -> None:
        return None

    monkeypatch.setattr(main_module, "close_app_db", fake_close_app_db)


def test_public_site_targets_console_instead_of_ops(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    monkeypatch.setattr(main_module.settings, "web_frontend_url", "http://127.0.0.1:5185")
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "控制台" in body
    assert "http://127.0.0.1:5185/login" in body
    assert "/console/login" not in body
    assert "35m.ops.adminApiKey" not in body


def test_public_site_defaults_to_same_origin_console_for_non_local_hosts(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    monkeypatch.setattr(main_module.settings, "web_frontend_url", "")
    monkeypatch.setattr(main_module.settings, "site_console_url", "")
    app = create_app()

    with TestClient(app, base_url="https://35m.ai") as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "/console/login" in body
    assert "http://127.0.0.1:5185/login" not in body


def test_google_callback_redirects_back_to_console_login(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    monkeypatch.setattr(main_module.settings, "web_frontend_url", "http://127.0.0.1:5185")
    monkeypatch.setattr(main_module.settings, "google_auth_redirect_url", "")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_login_with_google(self: SessionAuthService, *, code: str, state: str, redirect_uri: str) -> dict:
        del self
        assert code == "ok"
        assert state == "state-ok"
        assert redirect_uri == "http://testserver/auth/google/callback"
        return {
            "provider": "google",
            "session_token": "sess_google_console",
            "expires_in_seconds": 1209600,
            "next_path": "/settings",
        }

    monkeypatch.setattr(SessionAuthService, "login_with_google", fake_login_with_google)

    with TestClient(app) as client:
        response = client.get(
            "/auth/google/callback",
            params={"code": "ok", "state": "state-ok"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == "http://127.0.0.1:5185/login#session_token=sess_google_console&next=/settings"


def test_google_callback_redirects_to_same_origin_console_in_production_mode(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    monkeypatch.setattr(main_module.settings, "web_frontend_url", "")
    monkeypatch.setattr(main_module.settings, "site_console_url", "")
    monkeypatch.setattr(main_module.settings, "google_auth_redirect_url", "")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_login_with_google(self: SessionAuthService, *, code: str, state: str, redirect_uri: str) -> dict:
        del self
        assert code == "ok"
        assert state == "state-ok"
        assert redirect_uri == "https://35m.ai/auth/google/callback"
        return {
            "provider": "google",
            "session_token": "sess_google_console",
            "expires_in_seconds": 1209600,
            "next_path": "/settings",
        }

    monkeypatch.setattr(SessionAuthService, "login_with_google", fake_login_with_google)

    with TestClient(app, base_url="https://35m.ai") as client:
        response = client.get(
            "/auth/google/callback",
            params={"code": "ok", "state": "state-ok"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == "/console/login#session_token=sess_google_console&next=/settings"


def test_google_login_url_uses_local_callback_for_local_requests(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    monkeypatch.setattr(main_module.settings, "google_auth_redirect_url", "https://35m.ai/auth/google/callback")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_get_google_login_url(
        self: SessionAuthService,
        *,
        next_path: str,
        redirect_uri: str,
    ) -> str:
        del self
        assert next_path == "/settings"
        assert redirect_uri == "http://testserver/auth/google/callback"
        return "https://accounts.google.com/mock-auth"

    monkeypatch.setattr(SessionAuthService, "get_google_login_url", fake_get_google_login_url)

    with TestClient(app) as client:
        response = client.get("/auth/google/url", params={"next": "/settings"})

    assert response.status_code == 200
    assert response.json()["url"] == "https://accounts.google.com/mock-auth"


def test_wechat_login_url_reports_not_implemented(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/auth/wechat/url")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "wechat",
        "enabled": False,
        "message": "not_implemented",
    }


def test_retired_legacy_studio_routes_are_not_registered(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    app = create_app()
    registered_paths = {route.path for route in app.routes}

    assert "/api/app/assets/asset_list" not in registered_paths
    assert "/api/app/workflow-records/record_list" not in registered_paths
    assert "/api/app/card-run-records/record_list" not in registered_paths
    assert "/api/app/model-catalog/list" not in registered_paths
    assert "/api/app/workflow-messages/list" not in registered_paths
    assert "/v1/billing-records" not in registered_paths
    assert "/v1/recharges" not in registered_paths
    assert "/v1/recharges/mock-pay" not in registered_paths
    assert "/v1/recharge-packages" not in registered_paths
    assert "/v1/recharges/creem-checkout" not in registered_paths
    assert "/v1/recharges/wechat-native" not in registered_paths
    assert "/v1/payments/creem/webhook" not in registered_paths
    assert "/v1/payments/wechat/webhook" not in registered_paths
    assert "/pay/success" not in registered_paths
