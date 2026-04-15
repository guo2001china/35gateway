from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.domains.platform.services import auth_sessions
from app.domains.platform.services.auth_sessions import SessionAuthService
from app.domains.platform.services.tencent_email import TencentEmailError, TencentEmailService


class _FakeAuthStore:
    def __init__(self) -> None:
        self.values: dict[str, tuple[int, str]] = {}
        self.deleted_keys: list[str] = []

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = (ttl, value)

    def delete(self, key: str) -> int:
        self.deleted_keys.append(key)
        self.values.pop(key, None)
        return 1


def test_tencent_email_service_builds_template_request(monkeypatch) -> None:
    monkeypatch.setattr(settings, "tencent_email_secret_id", "sid")
    monkeypatch.setattr(settings, "tencent_email_secret_key", "skey")
    monkeypatch.setattr(settings, "tencent_email_region", "ap-guangzhou")
    monkeypatch.setattr(settings, "tencent_email_from_email", "35m <noreply@example.com>")
    monkeypatch.setattr(settings, "tencent_email_reply_to", "reply@example.com")
    monkeypatch.setattr(settings, "tencent_email_template_id_login", "1001")

    from tencentcloud.common import credential
    from tencentcloud.ses.v20201002 import ses_client

    captured: dict[str, object] = {}

    class _FakeCredential:
        def __init__(self, secret_id: str, secret_key: str) -> None:
            captured["credential"] = (secret_id, secret_key)

    class _FakeSesClient:
        def __init__(self, cred: object, region: str, profile: object) -> None:
            del cred, profile
            captured["region"] = region

        def SendEmail(self, request: object):
            captured["request"] = request

            class _Response:
                MessageId = "msg-001"

            return _Response()

    monkeypatch.setattr(credential, "Credential", _FakeCredential)
    monkeypatch.setattr(ses_client, "SesClient", _FakeSesClient)

    TencentEmailService().send_login_code(email="user@example.com", code="123456", ttl_seconds=300)

    request = captured["request"]
    assert captured["credential"] == ("sid", "skey")
    assert captured["region"] == "ap-guangzhou"
    assert getattr(request, "FromEmailAddress") == "35m <noreply@example.com>"
    assert getattr(request, "ReplyToAddresses") == "reply@example.com"
    assert getattr(request, "Destination") == ["user@example.com"]
    assert getattr(request, "Subject") == "35m.ai 登录验证码"
    assert getattr(request, "TriggerType") == 1
    assert getattr(getattr(request, "Template"), "TemplateID") == 1001
    assert json.loads(getattr(getattr(request, "Template"), "TemplateData")) == {
        "code": "123456",
        "ttl_minutes": 5,
    }


def test_send_email_code_uses_tencent_provider(monkeypatch) -> None:
    fake_auth_store = _FakeAuthStore()
    monkeypatch.setattr(auth_sessions, "get_auth_store", lambda: fake_auth_store)
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "auth_email_provider", "tencent")
    monkeypatch.setattr(settings, "auth_email_code_ttl_seconds", 300)

    captured: dict[str, object] = {}

    def fake_send_login_code(self: TencentEmailService, *, email: str, code: str, ttl_seconds: int) -> None:
        del self
        captured["email"] = email
        captured["code"] = code
        captured["ttl_seconds"] = ttl_seconds

    monkeypatch.setattr(TencentEmailService, "send_login_code", fake_send_login_code)

    result = SessionAuthService(db=object()).send_email_code(email="user@example.com")

    assert result == {
        "provider": "email_otp",
        "email": "user@example.com",
        "expires_in_seconds": 300,
        "debug_code": None,
    }
    assert captured["email"] == "user@example.com"
    assert captured["ttl_seconds"] == 300

    stored_ttl, stored_payload = fake_auth_store.values["auth:email-code:user@example.com"]
    assert stored_ttl == 300
    payload = json.loads(stored_payload)
    assert payload["email"] == "user@example.com"
    assert payload["code"] == captured["code"]
    assert len(str(payload["code"])) == 6


def test_send_email_code_rolls_back_cached_code_on_tencent_failure(monkeypatch) -> None:
    fake_auth_store = _FakeAuthStore()
    monkeypatch.setattr(auth_sessions, "get_auth_store", lambda: fake_auth_store)
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "auth_email_provider", "tencent")
    monkeypatch.setattr(settings, "auth_email_code_ttl_seconds", 300)

    def fake_send_login_code(self: TencentEmailService, *, email: str, code: str, ttl_seconds: int) -> None:
        del self, email, code, ttl_seconds
        raise TencentEmailError("tencent_email_send_failed:mocked")

    monkeypatch.setattr(TencentEmailService, "send_login_code", fake_send_login_code)

    with pytest.raises(HTTPException) as exc_info:
        SessionAuthService(db=object()).send_email_code(email="user@example.com")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "tencent_email_send_failed:mocked"
    assert fake_auth_store.deleted_keys == ["auth:email-code:user@example.com"]
    assert "auth:email-code:user@example.com" not in fake_auth_store.values
