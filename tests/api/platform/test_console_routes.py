from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_access, require_user_session
from app.api.deps import get_db
from app.core.provider_catalog.types import ProviderConfig
from app.db.session import SessionLocal
from app.domains.platform.entities.entities import ApiKey, BillingRecord, ProviderAccount, ProviderRequest, Request, Task, User, UserAuthIdentity
from app.main import create_app
from app.core.security import hash_password
from app.domains.platform.services.auth_sessions import EMAIL_AUTH_PROVIDER, PASSWORD_AUTH_PROVIDER
from app.domains.platform.services.provider_accounts import ProviderAccountService
from app.domains.platform.services.recharge import RechargeService
from app.domains.platform.services.system_api_keys import SystemApiKeyService
from app.domains.platform.services.user_console import UserConsoleService


def test_account_route_returns_serialized_balance(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    class _Account:
        balance = Decimal("12.340000")
        status = "active"

    def fake_get_account(self: RechargeService, *, user_id: int):
        del self
        assert user_id == 21
        return _Account()

    monkeypatch.setattr(RechargeService, "get_account", fake_get_account)

    with TestClient(app) as client:
        response = client.get("/v1/account", headers={"Authorization": "Bearer sess_test"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 21,
        "balance": "12.340000",
        "status": "active",
    }


def test_user_api_key_routes_cover_list_create_update(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="api_key")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    list_calls: list[int] = []
    create_calls: list[tuple[int, str]] = []
    reveal_calls: list[tuple[int, int]] = []
    update_calls: list[tuple[int, int, str | None, str | None]] = []
    delete_calls: list[tuple[int, int]] = []

    def fake_list_api_keys(self: UserConsoleService, *, user_id: int):
        del self
        list_calls.append(user_id)
        return [
            {
                "id": 11,
                "key_name": "Default",
                "key_kind": "user",
                "key_prefix": "ak_api35_demo***",
                "api_key": None,
                "status": "active",
                "created_at": None,
                "last_used_at": None,
            }
        ]

    def fake_create_api_key(self: UserConsoleService, *, user_id: int, key_name: str):
        del self
        create_calls.append((user_id, key_name))
        return {
            "id": 12,
            "key_name": key_name,
            "key_kind": "user",
            "key_prefix": "ak_api35_new***",
            "api_key": "ak_api35_new_plaintext",
            "status": "active",
            "created_at": None,
            "last_used_at": None,
        }

    def fake_update_api_key(
        self: UserConsoleService,
        *,
        user_id: int,
        api_key_id: int,
        key_name: str | None,
        status: str | None,
    ):
        del self
        update_calls.append((user_id, api_key_id, key_name, status))
        return {
            "id": api_key_id,
            "key_name": key_name or "Updated",
            "key_kind": "user",
            "key_prefix": "ak_api35_new***",
            "api_key": None,
            "status": status or "disabled",
            "created_at": None,
            "last_used_at": None,
        }

    def fake_reveal_api_key(self: UserConsoleService, *, user_id: int, api_key_id: int):
        del self
        reveal_calls.append((user_id, api_key_id))
        return {
            "id": api_key_id,
            "key_name": "Console Key Updated",
            "key_kind": "user",
            "key_prefix": "ak_api35_new***",
            "api_key": "ak_api35_revealed_plaintext",
            "status": "active",
            "created_at": None,
            "last_used_at": None,
        }

    def fake_delete_api_key(self: UserConsoleService, *, user_id: int, api_key_id: int):
        del self
        delete_calls.append((user_id, api_key_id))
        return {
            "id": api_key_id,
            "key_name": "Console Key Updated",
            "key_kind": "user",
            "key_prefix": "ak_api35_new***",
            "api_key": None,
            "status": "deleted",
            "created_at": None,
            "last_used_at": None,
        }

    monkeypatch.setattr(UserConsoleService, "list_api_keys", fake_list_api_keys)
    monkeypatch.setattr(UserConsoleService, "create_api_key", fake_create_api_key)
    monkeypatch.setattr(UserConsoleService, "reveal_api_key", fake_reveal_api_key)
    monkeypatch.setattr(UserConsoleService, "update_api_key", fake_update_api_key)
    monkeypatch.setattr(UserConsoleService, "delete_api_key", fake_delete_api_key)

    with TestClient(app) as client:
        list_response = client.get("/v1/api-keys", headers={"Authorization": "Bearer ak_api35_demo"})
        create_response = client.post(
            "/v1/api-keys",
            headers={"Authorization": "Bearer ak_api35_demo"},
            json={"key_name": "Console Key"},
        )
        reveal_response = client.post(
            "/v1/api-keys/12/reveal",
            headers={"Authorization": "Bearer ak_api35_demo"},
        )
        update_response = client.patch(
            "/v1/api-keys/12",
            headers={"Authorization": "Bearer ak_api35_demo"},
            json={"key_name": "Console Key Updated", "status": "disabled"},
        )
        delete_response = client.delete(
            "/v1/api-keys/12",
            headers={"Authorization": "Bearer ak_api35_demo"},
        )

    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert reveal_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert list_calls == [21]
    assert create_calls == [(21, "Console Key")]
    assert reveal_calls == [(21, 12)]
    assert update_calls == [(21, 12, "Console Key Updated", "disabled")]
    assert delete_calls == [(21, 12)]
    assert reveal_response.json()["api_key"] == "ak_api35_revealed_plaintext"


def test_profile_and_system_default_api_key_routes_delegate_to_services(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="session")
    app.dependency_overrides[require_user_session] = lambda: UserAccessContext(user_id=21, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_get_profile(self: UserConsoleService, *, user_id: int):
        del self
        assert user_id == 21
        return {
            "user_id": 21,
            "user_no": "u_000021",
            "name": "Smoke User",
            "balance": "8.000000",
            "status": "active",
            "email": "smoke@35m.ai",
            "phone": None,
            "identities": [],
            "password_login_enabled": True,
            "password_updated_at": "2026-04-07T08:00:00+00:00",
            "created_at": None,
        }

    def fake_update_profile(self: UserConsoleService, *, user_id: int, name: str | None):
        del self
        assert user_id == 21
        assert name == "Renamed User"
        return {
            "user_id": 21,
            "user_no": "u_000021",
            "name": "Renamed User",
            "balance": "8.000000",
            "status": "active",
            "email": "smoke@35m.ai",
            "phone": None,
            "identities": [],
            "password_login_enabled": True,
            "password_updated_at": "2026-04-07T08:00:00+00:00",
            "created_at": None,
        }

    def fake_get_system_default(self: SystemApiKeyService, *, user_id: int):
        del self
        assert user_id == 21
        return {
            "id": 100,
            "key_name": "System Default",
            "key_kind": "system_default",
            "key_prefix": "ak_api35_sys***",
            "api_key": "ak_api35_system_default",
            "status": "active",
            "created_at": None,
            "last_used_at": None,
        }

    monkeypatch.setattr(UserConsoleService, "get_profile", fake_get_profile)
    monkeypatch.setattr(UserConsoleService, "update_profile", fake_update_profile)
    monkeypatch.setattr(SystemApiKeyService, "get_system_default_key_response", fake_get_system_default)

    with TestClient(app) as client:
        profile = client.get("/v1/profile", headers={"Authorization": "Bearer sess_demo"})
        updated = client.patch(
            "/v1/profile",
            headers={"Authorization": "Bearer sess_demo"},
            json={"name": "Renamed User"},
        )
        system_default = client.get("/v1/api-keys/system-default", headers={"Authorization": "Bearer sess_demo"})

    assert profile.status_code == 200
    assert updated.status_code == 200
    assert system_default.status_code == 200
    assert profile.json()["email"] == "smoke@35m.ai"
    assert profile.json()["password_login_enabled"] is True
    assert updated.json()["name"] == "Renamed User"
    assert system_default.json()["api_key"] == "ak_api35_system_default"


def test_async_task_console_routes_delegate_to_service(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_list_tasks(
        self: UserConsoleService,
        *,
        user_id: int,
        page: int,
        size: int,
        status: str | None,
        model: str | None,
        query: str | None,
    ):
        del self
        assert user_id == 21
        assert page == 2
        assert size == 10
        assert status == "processing"
        assert model == "veo"
        assert query == "task_7f8f"
        return (
            1,
            {
                "active_count": 2,
                "pending_billing_count": 3,
                "completed_count": 10,
                "failed_or_waived_count": 1,
            },
            [
                {
                    "task_id": "task_7f8f",
                    "request_id": "req_demo",
                    "model": "veo-3.1",
                    "route_group": "veo",
                    "route_type": "video",
                    "provider_code": "google_veo",
                    "provider_account_id": None,
                    "provider_account_short_id": None,
                    "provider_account_owner_type": None,
                    "provider_task_id": "upstream_demo",
                    "task_status": "processing",
                    "billing_status": "pending",
                    "result_available": False,
                    "created_at": None,
                    "updated_at": None,
                    "finished_at": None,
                }
            ],
        )

    def fake_get_task_detail(self: UserConsoleService, *, user_id: int, task_id: str):
        del self
        assert user_id == 21
        assert task_id == "task_7f8f"
        return {
            "task_id": task_id,
            "request_id": "req_demo",
            "model": "veo-3.1",
            "route_group": "veo",
            "route_type": "video",
            "request_path": "/v1/veo",
            "provider_code": "google_veo",
            "provider_account_id": None,
            "provider_account_short_id": None,
            "provider_account_owner_type": None,
            "provider_task_id": "upstream_demo",
            "task_status": "processing",
            "billing_status": "pending",
            "power_amount": "1600.000000",
            "sale_amount": "1.60000000",
            "created_at": None,
            "updated_at": None,
            "finished_at": None,
            "result_payload": None,
            "result_urls": [],
            "error_message": None,
        }

    monkeypatch.setattr(UserConsoleService, "list_tasks_paginated", fake_list_tasks)
    monkeypatch.setattr(UserConsoleService, "get_task_detail", fake_get_task_detail)

    with TestClient(app) as client:
        list_response = client.get(
            "/v1/async-tasks?page=2&size=10&status=processing&model=veo&query=task_7f8f",
            headers={"Authorization": "Bearer sess_demo"},
        )
        detail_response = client.get(
            "/v1/async-tasks/task_7f8f",
            headers={"Authorization": "Bearer sess_demo"},
        )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert list_response.json()["summary"]["pending_billing_count"] == 3
    assert list_response.json()["items"][0]["task_id"] == "task_7f8f"
    assert detail_response.json()["request_id"] == "req_demo"


def test_provider_account_routes_delegate_to_service(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    calls: list[tuple[str, tuple | dict | None]] = []

    provider_options = [
        {
            "provider_code": "openrouter",
            "provider_name": "OpenRouter",
            "supports_balance_sync": True,
            "auth_fields": [{"field_name": "api_key", "label": "API Key", "required": True, "secret": True}],
        }
    ]
    account_payload = {
        "id": 1,
        "short_id": "or_demo01",
        "owner_type": "user",
        "user_id": 21,
        "provider_code": "openrouter",
        "provider_name": "OpenRouter",
        "display_name": "我的 OpenRouter",
        "status": "active",
        "routing_enabled": True,
        "priority": 10,
        "base_url_override": None,
        "verification_status": "verified",
        "last_verified_at": None,
        "last_verification_error": None,
        "balance_status": "ok",
        "balance_amount": "12.5",
        "balance_currency": "USD",
        "balance_updated_at": None,
        "notes": None,
        "supports_balance_sync": True,
    }

    def fake_list_provider_options(self: ProviderAccountService):
        del self
        calls.append(("list_provider_options", None))
        return provider_options

    def fake_list_user_accounts(self: ProviderAccountService, *, user_id: int):
        del self
        calls.append(("list_user_accounts", (user_id,)))
        return [account_payload]

    def fake_create_user_account(self: ProviderAccountService, *, user_id: int, payload: dict):
        del self
        calls.append(("create_user_account", {"user_id": user_id, "payload": payload}))
        return account_payload

    def fake_update_user_account(self: ProviderAccountService, *, user_id: int, account_id: int, payload: dict):
        del self
        calls.append(("update_user_account", {"user_id": user_id, "account_id": account_id, "payload": payload}))
        return {**account_payload, "display_name": payload.get("display_name", account_payload["display_name"])}

    def fake_delete_user_account(self: ProviderAccountService, *, user_id: int, account_id: int):
        del self
        calls.append(("delete_user_account", {"user_id": user_id, "account_id": account_id}))
        return {**account_payload, "status": "deleted"}

    def fake_verify_user_account(self: ProviderAccountService, *, user_id: int, account_id: int):
        del self
        calls.append(("verify_user_account", {"user_id": user_id, "account_id": account_id}))
        return account_payload

    def fake_sync_balance_user_account(self: ProviderAccountService, *, user_id: int, account_id: int):
        del self
        calls.append(("sync_balance_user_account", {"user_id": user_id, "account_id": account_id}))
        return account_payload

    monkeypatch.setattr(ProviderAccountService, "list_provider_options", fake_list_provider_options)
    monkeypatch.setattr(ProviderAccountService, "list_user_accounts", fake_list_user_accounts)
    monkeypatch.setattr(ProviderAccountService, "create_user_account", fake_create_user_account)
    monkeypatch.setattr(ProviderAccountService, "update_user_account", fake_update_user_account)
    monkeypatch.setattr(ProviderAccountService, "delete_user_account", fake_delete_user_account)
    monkeypatch.setattr(ProviderAccountService, "verify_user_account", fake_verify_user_account)
    monkeypatch.setattr(ProviderAccountService, "sync_balance_user_account", fake_sync_balance_user_account)

    with TestClient(app) as client:
        providers_response = client.get("/v1/provider-accounts/providers", headers={"Authorization": "Bearer sess_demo"})
        list_response = client.get("/v1/provider-accounts", headers={"Authorization": "Bearer sess_demo"})
        create_response = client.post(
            "/v1/provider-accounts",
            headers={"Authorization": "Bearer sess_demo"},
            json={
                "provider_code": "openrouter",
                "display_name": "我的 OpenRouter",
                "credential_payload": {"api_key": "sk-demo"},
                "priority": 10,
            },
        )
        update_response = client.patch(
            "/v1/provider-accounts/1",
            headers={"Authorization": "Bearer sess_demo"},
            json={"display_name": "更新后的账号"},
        )
        verify_response = client.post("/v1/provider-accounts/1/verify", headers={"Authorization": "Bearer sess_demo"})
        balance_response = client.post(
            "/v1/provider-accounts/1/sync-balance",
            headers={"Authorization": "Bearer sess_demo"},
        )
        delete_response = client.delete("/v1/provider-accounts/1", headers={"Authorization": "Bearer sess_demo"})

    assert providers_response.status_code == 200
    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert verify_response.status_code == 200
    assert balance_response.status_code == 200
    assert delete_response.status_code == 200
    assert providers_response.json()[0]["provider_code"] == "openrouter"
    assert list_response.json()[0]["short_id"] == "or_demo01"
    assert delete_response.json()["status"] == "deleted"
    assert any(name == "verify_user_account" for name, _ in calls)
    assert any(name == "sync_balance_user_account" for name, _ in calls)


def test_provider_account_service_crud_for_user_round_trip() -> None:
    user_no = f"u_{uuid4().hex[:12]}"

    with SessionLocal() as db:
        user = User(
            user_no=user_no,
            name="Provider Account User",
            balance=Decimal("0"),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = ProviderAccountService(db)
        created = service.create_user_account(
            user_id=user.id,
            payload={
                "provider_code": "openrouter",
                "display_name": "Live Smoke Account",
                "credential_payload": {"api_key": "or-test-live-smoke"},
                "priority": 10,
                "notes": "created in test",
            },
        )
        assert created["owner_type"] == "user"
        assert created["provider_code"] == "openrouter"
        assert created["display_name"] == "Live Smoke Account"
        assert created["notes"] == "created in test"
        assert created["routing_enabled"] is True

        updated = service.update_user_account(
            user_id=user.id,
            account_id=created["id"],
            payload={
                "display_name": "Live Smoke Account Updated",
                "notes": "",
                "priority": 20,
                "routing_enabled": False,
            },
        )
        assert updated["display_name"] == "Live Smoke Account Updated"
        assert updated["notes"] is None
        assert updated["priority"] == 20
        assert updated["routing_enabled"] is True

        deleted = service.delete_user_account(user_id=user.id, account_id=created["id"])
        assert deleted["status"] == "deleted"


def test_provider_account_service_openrouter_verify_uses_authenticated_endpoint(monkeypatch) -> None:
    user_no = f"u_{uuid4().hex[:12]}"

    def fake_httpx_get(url: str, *, headers=None, timeout=None, params=None):
        del timeout, params
        request = httpx.Request("GET", url, headers=headers)
        if url.endswith("/credits"):
            return httpx.Response(401, request=request, text="Missing Authentication header")
        return httpx.Response(200, request=request, json={"ok": True})

    monkeypatch.setattr("app.domains.platform.services.provider_accounts.httpx.get", fake_httpx_get)

    with SessionLocal() as db:
        user = User(
            user_no=user_no,
            name="Provider Verify User",
            balance=Decimal("0"),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = ProviderAccountService(db)
        created = service.create_user_account(
            user_id=user.id,
            payload={
                "provider_code": "openrouter",
                "display_name": "Verify Failure Account",
                "credential_payload": {"api_key": "or-invalid"},
                "priority": 10,
            },
        )

        try:
            service.verify_user_account(user_id=user.id, account_id=created["id"])
            raise AssertionError("verify_user_account should have failed for invalid openrouter credentials")
        except HTTPException as exc:
            assert exc.status_code == 401
            assert str(exc.detail).startswith("provider_account_verify_failed:")

        db.refresh(db.get(ProviderAccount, created["id"]))
        row = db.get(ProviderAccount, created["id"])
        assert row is not None
        assert row.verification_status == "failed"
        assert row.last_verification_error is not None

        db.delete(row)
        db.delete(user)
        db.commit()


def test_provider_account_service_syncs_platform_accounts_from_env(monkeypatch) -> None:
    provider_code = "openrouter_sync_test"
    provider = ProviderConfig(
        provider_code=provider_code,
        provider_name="OpenRouter",
        adapter_key="openai",
        base_url="https://openrouter.ai/api/v1",
        auth_type="bearer",
        auth_config={"api_key": "or-env-sync"},
    )

    monkeypatch.setattr(
        "app.domains.platform.services.provider_accounts.list_providers",
        lambda: [provider],
    )
    monkeypatch.setattr(
        ProviderAccountService,
        "list_provider_options",
        lambda self: [
            {
                "provider_code": provider_code,
                "provider_name": "OpenRouter Sync Test",
                "auth_fields": [{"field_name": "api_key", "label": "API Key", "required": True, "secret": True}],
                "supports_balance_sync": False,
            }
        ],
    )

    with SessionLocal() as db:
        service = ProviderAccountService(db)
        first = service.sync_platform_accounts_from_env()
        second = service.sync_platform_accounts_from_env()
        db.query(ProviderAccount).filter(ProviderAccount.provider_code == provider_code).delete(synchronize_session=False)
        db.commit()

    assert len(first) == 1
    assert len(second) == 1
    assert first[0]["provider_code"] == provider_code
    assert second[0]["provider_code"] == provider_code
    assert first[0]["short_id"] == second[0]["short_id"]
    assert first[0]["notes"].startswith("[env-sync]")


def test_get_profile_includes_password_login_summary() -> None:
    user_no = f"u_{uuid4().hex[:12]}"
    email = f"console-profile-{uuid4().hex[:8]}@35m.ai"
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        user = User(
            user_no=user_no,
            name="Console Profile User",
            balance=Decimal("12.340000"),
            status="active",
        )
        db.add(user)
        db.flush()
        db.add(
            UserAuthIdentity(
                user_id=user.id,
                provider=EMAIL_AUTH_PROVIDER,
                provider_user_id=email,
                email=email,
                profile={"email": email},
                last_login_at=now,
            )
        )
        db.add(
            UserAuthIdentity(
                user_id=user.id,
                provider=PASSWORD_AUTH_PROVIDER,
                provider_user_id=email,
                email=email,
                password_hash=hash_password("Password#123"),
                password_updated_at=now,
                profile={"email": email},
                last_login_at=now,
            )
        )
        db.commit()
        profile = UserConsoleService(db).get_profile(user_id=user.id)

    assert profile["email"] == email
    assert profile["password_login_enabled"] is True
    assert profile["password_updated_at"] is not None
    assert datetime.fromisoformat(profile["password_updated_at"]).timestamp() == now.timestamp()
    assert {item["provider"] for item in profile["identities"]} == {EMAIL_AUTH_PROVIDER, PASSWORD_AUTH_PROVIDER}


def test_user_logs_use_public_model_codes_for_fixed_public_routes(monkeypatch) -> None:
    app = create_app()

    class _Snapshot:
        @staticmethod
        def resolve_public_model_code(*, route_group: str, model_code: str | None) -> str | None:
            if route_group == "seedream" and model_code == "doubao-seedream-4-5-251128":
                return "doubao-seedream-4.5"
            return model_code

    monkeypatch.setattr(
        "app.domains.platform.services.user_console.get_platform_config_snapshot",
        lambda: _Snapshot(),
    )

    user_name = f"Console Smoke {uuid4().hex[:8]}"
    with SessionLocal() as db:
        user = User(
            user_no=f"u_{uuid4().hex[:12]}",
            name=user_name,
            balance=Decimal("1000.000000"),
            status="active",
        )
        db.add(user)
        db.flush()
        api_key = ApiKey(
            user_id=user.id,
            key_name="Console Key",
            key_kind="user",
            key_plaintext=f"ak_api35_console_{uuid4().hex[:12]}",
            key_hash=f"hash_{uuid4().hex}",
            status="active",
        )
        db.add(api_key)
        db.flush()

        now = datetime.now(timezone.utc)
        request_row = Request(
            request_id=f"req_{uuid4().hex[:24]}",
            route_mode="default",
            route_plan=["volcengine_seedream"],
            user_id=user.id,
            api_key_id=api_key.id,
            fallback_enabled=True,
            public_model_code="doubao-seedream-4.5",
            route_group="seedream",
            request_path="/v1/doubao-seedream-4.5",
            request_headers={},
            request_body={},
            response_body={"data": [{"url": "https://example.com/image.jpg"}]},
            status="succeeded",
            started_at=now,
            ended_at=now,
            duration_ms=800,
        )
        db.add(request_row)
        db.flush()
        db.add(
            ProviderRequest(
                request_id=request_row.id,
                attempt_no=1,
                provider_code="volcengine_seedream",
                execution_model_code="doubao-seedream-4-5-251128",
                provider_request_id="seedream_req",
                http_status_code=200,
                error_message=None,
                fallback_reason=None,
                request_payload={"prompt": "blue tech poster"},
                response_payload={"ok": True},
                status="succeeded",
                started_at=now,
                ended_at=now,
                duration_ms=700,
            )
        )
        db.add(
            BillingRecord(
                request_id=request_row.id,
                user_id=user.id,
                api_key_id=api_key.id,
                provider_code="volcengine_seedream",
                public_model_code="doubao-seedream-4.5",
                route_group="seedream",
                billing_mode="final",
                billing_unit="image",
                billing_snapshot={"power_amount": "277.800000"},
                sale_amount=Decimal("0.2778"),
                sale_currency="CNY",
                cost_amount=Decimal("0.2500"),
                cost_currency="CNY",
                margin_amount=Decimal("0.0278"),
                power_amount=Decimal("277.800000"),
                status="succeeded",
                created_at=now,
            )
        )
        db.commit()
        user_id = user.id
        request_id = request_row.request_id

    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=user_id, auth_mode="session")

    with TestClient(app) as client:
        logs = client.get("/v1/logs", headers={"Authorization": "Bearer sess_demo"})
        detail = client.get(
            f"/v1/logs/{request_id}",
            headers={"Authorization": "Bearer sess_demo"},
        )

    assert logs.status_code == 200
    assert detail.status_code == 200
    assert logs.json()["items"][0]["model"] == "doubao-seedream-4.5"
    assert detail.json()["model"] == "doubao-seedream-4.5"


def test_user_log_detail_hides_top_level_error_for_succeeded_fallback_request() -> None:
    app = create_app()

    with SessionLocal() as db:
        user = User(
            user_no=f"u_{uuid4().hex[:12]}",
            name=f"Fallback Detail User {uuid4().hex[:8]}",
            balance=Decimal("1000.000000"),
            status="active",
        )
        db.add(user)
        db.flush()
        api_key = ApiKey(
            user_id=user.id,
            key_name="Fallback Detail Key",
            key_kind="user",
            key_plaintext=f"ak_api35_fallback_{uuid4().hex[:12]}",
            key_hash=f"hash_{uuid4().hex}",
            status="active",
        )
        db.add(api_key)
        db.flush()
        yunwu_account = ProviderAccount(
            short_id=f"yw_{uuid4().hex[:6]}",
            owner_type="platform",
            user_id=None,
            provider_code="yunwu_openai",
            display_name="Yunwu Demo",
            status="active",
            routing_enabled=True,
            priority=10,
            credential_payload={"api_key": "demo"},
            verification_status="verified",
            balance_status="unsupported",
        )
        openai_account = ProviderAccount(
            short_id=f"oa_{uuid4().hex[:6]}",
            owner_type="platform",
            user_id=None,
            provider_code="openai_official",
            display_name="OpenAI Demo",
            status="active",
            routing_enabled=True,
            priority=20,
            credential_payload={"api_key": "demo"},
            verification_status="verified",
            balance_status="unsupported",
        )
        db.add(yunwu_account)
        db.add(openai_account)
        db.flush()

        now = datetime.now(timezone.utc)
        request_row = Request(
            request_id=f"req_{uuid4().hex[:24]}",
            route_mode="default",
            route_plan=["yunwu_openai", "openai_official"],
            user_id=user.id,
            api_key_id=api_key.id,
            fallback_enabled=True,
            public_model_code="gpt-5.4",
            route_group="openai",
            request_path="/v1/chat/completions",
            request_headers={"x-api35-chain": "yunwu_openai,openai_official"},
            request_body={"model": "gpt-5.4", "messages": [{"role": "user", "content": "OK"}]},
            response_body={"id": "chatcmpl_demo", "model": "gpt-5.4", "choices": [{"message": {"content": "OK"}}]},
            status="succeeded",
            started_at=now,
            ended_at=now,
            duration_ms=65404,
        )
        db.add(request_row)
        db.flush()
        db.add(
            ProviderRequest(
                request_id=request_row.id,
                attempt_no=1,
                provider_code="yunwu_openai",
                provider_account_id=yunwu_account.id,
                provider_account_short_id=yunwu_account.short_id,
                provider_account_owner_type="platform",
                execution_model_code="gpt-5.4",
                provider_request_id=None,
                http_status_code=None,
                error_message="ReadTimeout",
                fallback_reason=None,
                request_payload={"model": "gpt-5.4"},
                response_payload={"error": "ReadTimeout"},
                status="failed",
                started_at=now,
                ended_at=now,
                duration_ms=61461,
            )
        )
        db.add(
            ProviderRequest(
                request_id=request_row.id,
                attempt_no=2,
                provider_code="openai_official",
                provider_account_id=openai_account.id,
                provider_account_short_id=openai_account.short_id,
                provider_account_owner_type="platform",
                execution_model_code="gpt-5.4",
                provider_request_id="chatcmpl_demo",
                http_status_code=200,
                error_message=None,
                fallback_reason="ReadTimeout",
                request_payload={"model": "gpt-5.4"},
                response_payload={"id": "chatcmpl_demo"},
                status="succeeded",
                started_at=now,
                ended_at=now,
                duration_ms=3513,
            )
        )
        db.commit()
        user_id = user.id
        request_id = request_row.request_id

    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=user_id, auth_mode="session")

    with TestClient(app) as client:
        detail = client.get(
            f"/v1/logs/{request_id}",
            headers={"Authorization": "Bearer sess_demo"},
        )

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "succeeded"
    assert payload["error_message"] is None
    assert payload["chain"][0]["error_message"] == "ReadTimeout"
    assert payload["chain"][1]["error_message"] is None
    assert payload["chain"][1]["fallback_reason"] == "ReadTimeout"


def test_user_task_console_list_and_detail_round_trip() -> None:
    with SessionLocal() as db:
        user = User(
            user_no=f"u_{uuid4().hex[:12]}",
            name=f"Task Console User {uuid4().hex[:8]}",
            balance=Decimal("1000.000000"),
            status="active",
        )
        db.add(user)
        db.flush()
        api_key = ApiKey(
            user_id=user.id,
            key_name="Task Console Key",
            key_kind="user",
            key_plaintext=f"ak_api35_task_{uuid4().hex[:12]}",
            key_hash=f"hash_{uuid4().hex}",
            status="active",
        )
        db.add(api_key)
        db.flush()

        now = datetime.now(timezone.utc)
        request_row = Request(
            request_id=f"req_{uuid4().hex[:24]}",
            route_mode="default",
            route_plan=["google_veo"],
            user_id=user.id,
            api_key_id=api_key.id,
            fallback_enabled=True,
            public_model_code="veo-3.1",
            route_group="veo",
            request_path="/v1/veo",
            request_headers={},
            request_body={"model": "veo-3.1"},
            response_body=None,
            status="succeeded",
            started_at=now,
            ended_at=now,
            duration_ms=1200,
        )
        db.add(request_row)
        db.flush()
        task_row = Task(
            platform_task_id=f"task_{uuid4().hex[:24]}",
            request_id=request_row.id,
            provider_code="google_veo",
            provider_account_id=None,
            provider_account_short_id=None,
            provider_account_owner_type=None,
            public_model_code="veo-3.1",
            provider_task_id="veo_task_demo",
            status="completed",
            result_payload={"data": [{"url": "https://example.com/video.mp4"}]},
            created_at=now,
            updated_at=now,
            finished_at=now,
        )
        db.add(task_row)
        db.add(
            BillingRecord(
                request_id=request_row.id,
                user_id=user.id,
                api_key_id=api_key.id,
                provider_code="google_veo",
                public_model_code="veo-3.1",
                route_group="veo",
                billing_mode="final",
                billing_unit="video",
                billing_snapshot={"power_amount": "1600.000000"},
                sale_amount=Decimal("1.60000000"),
                sale_currency="CNY",
                cost_amount=Decimal("1.20000000"),
                cost_currency="CNY",
                margin_amount=Decimal("0.40000000"),
                power_amount=Decimal("1600.000000"),
                status="succeeded",
                created_at=now,
            )
        )
        db.commit()
        task_public_id = task_row.platform_task_id

        task_total, task_summary, task_items = UserConsoleService(db).list_tasks_paginated(user_id=user.id, page=1, size=20)
        task_detail = UserConsoleService(db).get_task_detail(user_id=user.id, task_id=task_public_id)

    assert task_total == 1
    assert task_summary["completed_count"] == 1
    assert task_items[0]["model"] == "veo-3.1"
    assert task_items[0]["billing_status"] == "succeeded"
    assert task_items[0]["result_available"] is True
    assert task_detail["task_id"] == task_public_id
    assert task_detail["result_urls"] == ["https://example.com/video.mp4"]
    assert task_detail["sale_amount"] == "1.60000000"
