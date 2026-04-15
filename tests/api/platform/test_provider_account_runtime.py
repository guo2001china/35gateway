from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import Request

from app.api.auth import ApiKeyContext
from app.db.session import SessionLocal
from app.domains.platform.entities.entities import (
    ApiKey,
    BillingRecord,
    BusinessEvent,
    ProviderAccount,
    ProviderRequest,
    Request as RequestRow,
    User,
    UserGrowthProfile,
)
from app.domains.platform.services.provider_account_runtime import ProviderAccountRuntimeService
from app.domains.platform.services.proxy_execution import execute_proxy_request
from app.domains.platform.services.routing import RoutePlan, RouteResult, RoutingService


def _request_with_id(request_id: str, path: str = "/v1/chat/completions") -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
            "root_path": "",
            "http_version": "1.1",
        }
    )
    request.state.request_id = request_id
    return request


def test_provider_account_runtime_expands_user_then_platform_attempts() -> None:
    user_no = f"u_{uuid4().hex[:12]}"
    with SessionLocal() as db:
        user = User(user_no=user_no, name="Runtime Expand User", balance=Decimal("10"), status="active")
        db.add(user)
        db.commit()
        db.refresh(user)

        user_account = ProviderAccount(
            short_id=f"or_{uuid4().hex[:6]}",
            owner_type="user",
            user_id=user.id,
            provider_code="openrouter",
            display_name="User OpenRouter",
            status="active",
            routing_enabled=True,
            priority=10,
            credential_payload={"api_key": "user-key"},
        )
        platform_account = ProviderAccount(
            short_id=f"or_{uuid4().hex[:6]}",
            owner_type="platform",
            user_id=None,
            provider_code="openrouter",
            display_name="Platform OpenRouter",
            status="active",
            routing_enabled=True,
            priority=20,
            credential_payload={"api_key": "platform-key"},
        )
        db.add_all([user_account, platform_account])
        db.commit()
        db.refresh(user_account)
        db.refresh(platform_account)
        expected_user_short_id = user_account.short_id

        runtime_service = ProviderAccountRuntimeService(db)
        attempts = runtime_service.expand_attempts(
            user_id=user.id,
            attempts=[
                RouteResult(
                    provider_code="openrouter",
                    public_model_code="openrouter-free",
                    execution_model_code="openrouter-free",
                    pricing_strategy="text_tokens",
                    route_group="openai",
                )
            ],
        )
        first_short_id = attempts[0].provider_account_short_id
        first_owner_type = attempts[0].provider_account_owner_type
        first_api_key = attempts[0].provider.auth_config["api_key"] if attempts[0].provider else None
        has_platform_attempt = any(item.provider_account_owner_type == "platform" for item in attempts[1:])
        has_platform_api_key = any(
            item.provider is not None and item.provider.auth_config.get("api_key") == "platform-key"
            for item in attempts[1:]
        )
        db.query(ProviderAccount).filter(ProviderAccount.id.in_([user_account.id, platform_account.id])).delete(
            synchronize_session=False
        )
        db.query(BusinessEvent).filter(BusinessEvent.user_id == user.id).delete(synchronize_session=False)
        db.query(UserGrowthProfile).filter(UserGrowthProfile.user_id == user.id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()

    assert first_short_id == expected_user_short_id
    assert first_owner_type == "user"
    assert has_platform_attempt is True
    assert first_api_key == "user-key"
    assert has_platform_api_key is True



@pytest.mark.anyio
async def test_execute_proxy_request_falls_back_from_user_account_to_platform_account(monkeypatch) -> None:
    user_no = f"u_{uuid4().hex[:12]}"
    request_id = f"req_{uuid4().hex[:16]}"

    with SessionLocal() as db:
        user = User(user_no=user_no, name="Runtime Fallback User", balance=Decimal("100"), status="active")
        db.add(user)
        db.flush()
        api_key = ApiKey(
            user_id=user.id,
            key_name="Runtime Key",
            key_kind="user_created",
            key_hash=f"hash_{uuid4().hex}",
            key_plaintext=None,
            status="active",
        )
        db.add(api_key)
        db.flush()

        user_account = ProviderAccount(
            short_id=f"or_{uuid4().hex[:6]}",
            owner_type="user",
            user_id=user.id,
            provider_code="openrouter",
            display_name="Bad User OpenRouter",
            status="active",
            routing_enabled=True,
            priority=10,
            credential_payload={"api_key": "bad-user-key"},
        )
        platform_account = ProviderAccount(
            short_id=f"or_{uuid4().hex[:6]}",
            owner_type="platform",
            user_id=None,
            provider_code="openrouter",
            display_name="Good Platform OpenRouter",
            status="active",
            routing_enabled=True,
            priority=20,
            credential_payload={"api_key": "good-platform-key"},
        )
        db.add_all([user_account, platform_account])
        db.commit()
        db.refresh(api_key)
        db.refresh(user_account)
        db.refresh(platform_account)
        user_short_id = user_account.short_id

        async def fake_invoke(self, ctx: dict):
            del self
            provider = ctx["provider"]
            api_key_value = str(provider.auth_config.get("api_key") or "")
            if api_key_value == "bad-user-key":
                request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
                response = httpx.Response(401, request=request, json={"error": "bad api key"})
                raise httpx.HTTPStatusError("bad key", request=request, response=response)
            return {
                "id": "chatcmpl_runtime_smoke",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "provider-account-runtime-ok"},
                        "finish_reason": "stop",
                    }
                ],
            }

        monkeypatch.setattr(
            "app.domains.platform.providers.openai.OpenAIAdapter.invoke",
            fake_invoke,
        )

        def fake_plan(self: RoutingService, **kwargs):
            del self, kwargs
            return RoutePlan(
                route_mode="default",
                attempts=[
                    RouteResult(
                        provider_code="openrouter",
                        public_model_code="openrouter-free",
                        execution_model_code="openrouter-free",
                        pricing_strategy="text_tokens",
                        route_group="openai",
                    )
                ],
                requested_providers=[],
            )

        monkeypatch.setattr(RoutingService, "plan", fake_plan)
        monkeypatch.setattr(RoutingService, "default_chain", lambda self, **kwargs: "openrouter")

        monkeypatch.setattr(
            "app.domains.platform.services.proxy_execution.provider_supports_payload",
            lambda **kwargs: True,
        )

        def fake_build_provider_options(self, **kwargs):
            attempts = kwargs["attempts"]
            return [
                {
                    "attempt_no": index,
                    "provider_code": attempt.provider_code,
                    "provider_name": attempt.provider.provider_name if attempt.provider else attempt.provider_code,
                    "provider_account_short_id": attempt.provider_account_short_id,
                    "provider_account_owner_type": attempt.provider_account_owner_type,
                    "model_code": attempt.execution_model_code,
                    "execution_model_code": attempt.execution_model_code,
                    "pricing_strategy": attempt.pricing_strategy,
                    "billing_unit": "request",
                    "estimated_amount": "0.01",
                    "estimated_power_amount": "0.01",
                    "currency": "USD",
                    "pricing_snapshot": {"power_amount": "0.01"},
                    "metrics": {"sample_ready": False, "latency": {}},
                    "rank": index,
                    "recommended": index == 1,
                }
                for index, attempt in enumerate(attempts, start=1)
            ]

        monkeypatch.setattr(
            "app.domains.platform.services.proxy_execution.ProviderOptionsService.build_provider_options",
            fake_build_provider_options,
        )
        monkeypatch.setattr(
            "app.domains.platform.services.proxy_execution.TaskControlService.ensure_non_negative_available_balance",
            lambda self, user_id: SimpleNamespace(balance=Decimal("100"), status="active"),
        )
        monkeypatch.setattr(
            "app.domains.platform.services.proxy_execution.TaskControlService.ensure_sufficient_available_balance",
            lambda self, user_id, power_amount: SimpleNamespace(balance=Decimal("100"), status="active"),
        )

        result = await execute_proxy_request(
            http_request=_request_with_id(request_id),
            ctx=ApiKeyContext(user_id=user.id, api_key_id=api_key.id, key_name="Runtime Key"),
            db=db,
            route_group="openai",
            requested_model="openrouter-free",
            provider_path="/chat/completions",
            payload={
                "model": "openrouter-free",
                "messages": [{"role": "user", "content": "say hi"}],
            },
            chain=None,
            allow_fallback=True,
        )

        request_row = db.query(RequestRow).filter(RequestRow.request_id == request_id).one()
        provider_rows = (
            db.query(ProviderRequest)
            .filter(ProviderRequest.request_id == request_row.id)
            .order_by(ProviderRequest.attempt_no.asc(), ProviderRequest.id.asc())
            .all()
        )
        result_content = result["choices"][0]["message"]["content"]
        provider_row_snapshot = [
            {
                "provider_account_short_id": row.provider_account_short_id,
                "provider_account_owner_type": row.provider_account_owner_type,
                "status": row.status,
            }
            for row in provider_rows
        ]
        db.query(ProviderRequest).filter(ProviderRequest.request_id == request_row.id).delete(synchronize_session=False)
        db.query(BillingRecord).filter(BillingRecord.request_id == request_row.id).delete(synchronize_session=False)
        db.query(RequestRow).filter(RequestRow.id == request_row.id).delete(synchronize_session=False)
        db.query(ApiKey).filter(ApiKey.id == api_key.id).delete(synchronize_session=False)
        db.query(ProviderAccount).filter(ProviderAccount.id.in_([user_account.id, platform_account.id])).delete(
            synchronize_session=False
        )
        db.query(BusinessEvent).filter(BusinessEvent.user_id == user.id).delete(synchronize_session=False)
        db.query(UserGrowthProfile).filter(UserGrowthProfile.user_id == user.id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()

    assert result_content == "provider-account-runtime-ok"
    assert len(provider_row_snapshot) >= 2
    assert provider_row_snapshot[0]["provider_account_short_id"] == user_short_id
    assert provider_row_snapshot[0]["provider_account_owner_type"] == "user"
    assert provider_row_snapshot[0]["status"] == "failed"
    assert provider_row_snapshot[1]["provider_account_owner_type"] == "platform"
    assert provider_row_snapshot[1]["status"] == "succeeded"
