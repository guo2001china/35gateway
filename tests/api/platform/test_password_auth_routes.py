from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.auth_sessions import SessionAuthService


def test_login_with_password_route_returns_session(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_login_with_password(
        self: SessionAuthService,
        *,
        email: str,
        password: str,
        growth_context: dict | None = None,
    ) -> dict:
        del self
        assert email == "test@35m.ai"
        assert password == "Password#123"
        assert growth_context is None
        return {
            "provider": "password_local",
            "session_token": "sess_api35_password_test",
            "expires_in_seconds": 1209600,
            "user": {
                "user_id": 9,
                "user_no": "U000009",
                "name": "password-user",
                "status": "active",
                "phone": None,
                "email": email,
            },
        }

    monkeypatch.setattr(SessionAuthService, "login_with_password", fake_login_with_password)

    with TestClient(app) as client:
        response = client.post(
            "/auth/login/password",
            json={"email": "test@35m.ai", "password": "Password#123"},
        )

    assert response.status_code == 201
    assert response.json()["provider"] == "password_local"
    assert response.json()["session_token"] == "sess_api35_password_test"
    assert response.json()["user"]["email"] == "test@35m.ai"


def test_register_with_password_route_returns_session(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_register_with_password(
        self: SessionAuthService,
        *,
        email: str,
        code: str,
        password: str,
        growth_context: dict | None = None,
    ) -> dict:
        del self
        assert email == "test@35m.ai"
        assert code == "123456"
        assert password == "Password#123"
        assert growth_context is None
        return {
            "provider": "password_local",
            "session_token": "sess_api35_password_register",
            "expires_in_seconds": 1209600,
            "user": {
                "user_id": 10,
                "user_no": "U000010",
                "name": "register-user",
                "status": "active",
                "phone": None,
                "email": email,
            },
        }

    monkeypatch.setattr(SessionAuthService, "register_with_password", fake_register_with_password)

    with TestClient(app) as client:
        response = client.post(
            "/auth/register/password",
            json={"email": "test@35m.ai", "code": "123456", "password": "Password#123"},
        )

    assert response.status_code == 201
    assert response.json()["provider"] == "password_local"
    assert response.json()["session_token"] == "sess_api35_password_register"
    assert response.json()["user"]["email"] == "test@35m.ai"
