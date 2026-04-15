from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_session
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.auth_sessions import SessionAuthService


def test_send_phone_code_route_returns_phone_payload(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_send_phone_code(self: SessionAuthService, *, phone: str) -> dict:
        del self
        assert phone == "+8613800138000"
        return {
            "provider": "phone_sms",
            "phone": phone,
            "expires_in_seconds": 300,
            "debug_code": "123456",
        }

    monkeypatch.setattr(SessionAuthService, "send_phone_code", fake_send_phone_code)

    with TestClient(app) as client:
        response = client.post("/auth/phone/send-code", json={"phone": "+8613800138000"})

    assert response.status_code == 201
    assert response.json() == {
        "provider": "phone_sms",
        "phone": "+8613800138000",
        "expires_in_seconds": 300,
        "debug_code": "123456",
    }


def test_login_with_phone_route_returns_session(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_login_with_phone(
        self: SessionAuthService,
        *,
        phone: str,
        code: str,
        growth_context: dict | None = None,
    ) -> dict:
        del self
        assert phone == "+8613800138000"
        assert code == "123456"
        assert growth_context is None
        return {
            "provider": "phone_sms",
            "session_token": "sess_api35_phone_test",
            "expires_in_seconds": 1209600,
            "user": {
                "user_id": 8,
                "user_no": "U000008",
                "name": "phone-user",
                "status": "active",
                "phone": phone,
                "email": None,
            },
        }

    monkeypatch.setattr(SessionAuthService, "login_with_phone", fake_login_with_phone)

    with TestClient(app) as client:
        response = client.post("/auth/login/phone", json={"phone": "+8613800138000", "code": "123456"})

    assert response.status_code == 201
    assert response.json()["provider"] == "phone_sms"
    assert response.json()["session_token"] == "sess_api35_phone_test"
    assert response.json()["user"]["phone"] == "+8613800138000"


def test_session_me_and_logout_routes_delegate_to_session_service(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_session] = lambda: UserAccessContext(
        user_id=21,
        auth_mode="session",
        session_id="sess_001",
        session_token="sess_api35_demo",
    )
    app.dependency_overrides[get_db] = lambda: iter([object()])

    class _SessionRecord:
        user_id = 21
        identity_id = 101
        provider = "email_otp"
        issued_at = "2026-03-30T00:00:00+00:00"

    def fake_get_session_record(self: SessionAuthService, token: str):
        del self
        assert token == "sess_api35_demo"
        return _SessionRecord()

    def fake_get_session_me(self: SessionAuthService, *, session_record):
        del self
        assert session_record.user_id == 21
        return {
            "auth_mode": "session",
            "provider": "email_otp",
            "issued_at": "2026-03-30T00:00:00+00:00",
            "last_login_at": "2026-03-30T00:00:00+00:00",
            "user": {
                "user_id": 21,
                "user_no": "U000021",
                "name": "Smoke User",
                "status": "active",
                "email": "smoke@35m.ai",
                "phone": None,
            },
        }

    def fake_revoke_session(self: SessionAuthService, *, token: str) -> bool:
        del self
        assert token == "sess_api35_demo"
        return True

    monkeypatch.setattr(SessionAuthService, "get_session_record", fake_get_session_record)
    monkeypatch.setattr(SessionAuthService, "get_session_me", fake_get_session_me)
    monkeypatch.setattr(SessionAuthService, "revoke_session", fake_revoke_session)

    with TestClient(app) as client:
        me = client.get("/auth/session/me", headers={"Authorization": "Bearer sess_api35_demo"})
        logout = client.post("/auth/session/logout", headers={"Authorization": "Bearer sess_api35_demo"})

    assert me.status_code == 200
    assert logout.status_code == 200
    assert me.json()["user"]["email"] == "smoke@35m.ai"
    assert logout.json() == {"revoked": True}
