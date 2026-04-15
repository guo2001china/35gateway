from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.auth_sessions import SessionAuthService


def test_send_email_code_route_returns_email_payload(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_send_email_code(self: SessionAuthService, *, email: str) -> dict:
        del self
        assert email == "test@35m.ai"
        return {
            "provider": "email_otp",
            "email": email,
            "expires_in_seconds": 300,
            "debug_code": "123456",
        }

    monkeypatch.setattr(SessionAuthService, "send_email_code", fake_send_email_code)

    with TestClient(app) as client:
        response = client.post("/auth/email/send-code", json={"email": "test@35m.ai"})

    assert response.status_code == 201
    assert response.json() == {
        "provider": "email_otp",
        "email": "test@35m.ai",
        "expires_in_seconds": 300,
        "debug_code": "123456",
    }


def test_login_with_email_route_returns_session(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_login_with_email(
        self: SessionAuthService,
        *,
        email: str,
        code: str,
        growth_context: dict | None = None,
    ) -> dict:
        del self
        assert email == "test@35m.ai"
        assert code == "123456"
        assert growth_context is None
        return {
            "provider": "email_otp",
            "session_token": "sess_api35_email_test",
            "expires_in_seconds": 1209600,
            "user": {
                "user_id": 7,
                "user_no": "U000007",
                "name": "test",
                "status": "active",
                "phone": None,
                "email": email,
            },
        }

    monkeypatch.setattr(SessionAuthService, "login_with_email", fake_login_with_email)

    with TestClient(app) as client:
        response = client.post("/auth/login/email", json={"email": "test@35m.ai", "code": "123456"})

    assert response.status_code == 201
    assert response.json()["provider"] == "email_otp"
    assert response.json()["session_token"] == "sess_api35_email_test"
    assert response.json()["user"]["email"] == "test@35m.ai"
