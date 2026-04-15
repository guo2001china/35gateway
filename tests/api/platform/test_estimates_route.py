from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService


def _estimate_response(*, route_group: str, model: str) -> dict[str, object]:
    provider = {
        "attempt_no": 1,
        "provider_code": "demo_provider",
        "provider_name": "Demo Provider",
        "model_code": model,
        "billing_unit": "request",
        "priority": 100,
        "estimated_amount": "1.00",
        "estimated_power_amount": "1000.00",
        "currency": "CNY",
        "pricing_snapshot": {"request_factors": {}},
        "metrics": {
            "window": "24h",
            "sample_count": 0,
            "success_count": 0,
            "success_rate": 0,
            "sample_ready": False,
            "latency": {
                "avg_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "sample_count": 0,
            },
        },
        "rank": 1,
        "recommended": True,
    }
    return {
        "route_group": route_group,
        "model": model,
        "route_mode": "default",
        "chain": ["demo_provider"],
        "request_factors": {},
        "selected_provider": provider,
        "cheapest_provider": provider,
        "provider_options": [provider],
        "required_power_amount": "1000.00",
        "missing_power_amount": "0",
        "balance_check_basis": {
            "mode": "max_provider_in_route_plan",
            "provider_code": "demo_provider",
            "provider_name": "Demo Provider",
            "required_power_amount": "1000.00",
            "missing_power_amount": "0",
        },
        "actual_charge_basis": {
            "mode": "actual_success_provider",
            "description": "Final charge uses the provider that actually succeeds.",
        },
        "account": {
            "balance": "10000.00",
            "available_balance": "10000.00",
            "sufficient_balance": True,
            "status": "active",
        },
    }


def _public_estimate_summary(*, model: str, quote_mode: str = "estimated") -> dict[str, object]:
    return {
        "model": model,
        "quote_mode": quote_mode,
        "route_mode": "default",
        "lowest_price": "1.00",
        "highest_price": "1.00",
        "currency": "CNY",
        "balance": {
            "available_amount": "10000.00",
            "enough_for_highest": True,
        },
        "request_factors": {},
    }


def test_estimates_route_uses_primary_public_model_for_sync_estimate(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="openai")
            if model_code == "gpt-5.4" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_proxy_request(*, ctx, db, route_group, requested_model, payload, chain, allow_fallback, metrics_window):
        del ctx, db
        captured.update(
            {
                "route_group": route_group,
                "requested_model": requested_model,
                "payload": payload,
                "chain": chain,
                "allow_fallback": allow_fallback,
                "metrics_window": metrics_window,
            }
        )
        return _estimate_response(route_group=route_group, model=str(requested_model))

    monkeypatch.setattr(estimates_route, "estimate_proxy_request", fake_estimate_proxy_request)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "gpt-5.4",
                "payload": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "hello",
                        }
                    ]
                },
                "chain": ["openai_official", "openrouter"],
                "fallback": False,
                "metrics_window": "7d",
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="gpt-5.4", quote_mode="estimated")
    assert captured == {
        "route_group": "openai",
        "requested_model": "gpt-5.4",
        "payload": {
            "model": "gpt-5.4",
            "messages": [
                {
                    "role": "user",
                    "content": "hello",
                }
            ],
        },
        "chain": "openai_official,openrouter",
        "allow_fallback": False,
        "metrics_window": "7d",
    }


def test_estimates_route_uses_async_estimator_for_video_model(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="veo31")
            if model_code == "veo-3.1-fast" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_task(
        self: AsyncTaskExecutionService,
        *,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, ctx
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
                "chain": chain,
                "fallback": fallback,
                "metrics_window": metrics_window,
            }
        )
        return _estimate_response(route_group=route_group, model=fixed_model_code)

    monkeypatch.setattr(AsyncTaskExecutionService, "estimate_task", fake_estimate_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "veo-3.1-fast",
                "payload": {
                    "prompt": "cinematic city skyline at sunrise",
                    "seconds": 8,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="veo-3.1-fast", quote_mode="exact")
    assert captured == {
        "route_group": "veo31",
        "fixed_model_code": "veo-3.1-fast",
        "payload": {
            "prompt": "cinematic city skyline at sunrise",
            "seconds": 8,
        },
        "chain": None,
        "fallback": None,
        "metrics_window": None,
    }


def test_estimates_route_uses_async_estimator_for_seedance_model(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="seedance")
            if model_code == "seedance-2.0-fast" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_task(
        self: AsyncTaskExecutionService,
        *,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, ctx
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
                "chain": chain,
                "fallback": fallback,
                "metrics_window": metrics_window,
            }
        )
        return _estimate_response(route_group=route_group, model=fixed_model_code)

    monkeypatch.setattr(AsyncTaskExecutionService, "estimate_task", fake_estimate_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "seedance-2.0-fast",
                "payload": {
                    "prompt": "cinematic city skyline at sunrise",
                    "seconds": 4,
                    "resolution": "720p",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="seedance-2.0-fast", quote_mode="exact")
    assert captured == {
        "route_group": "seedance",
        "fixed_model_code": "seedance-2.0-fast",
        "payload": {
            "prompt": "cinematic city skyline at sunrise",
            "seconds": 4,
            "resolution": "720p",
        },
        "chain": None,
        "fallback": None,
        "metrics_window": None,
    }


def test_estimates_route_returns_text_range_from_input_and_output_bounds(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="openai")
            if model_code == "gpt-5.4" and public_only
            else None
        ),
    )

    def fake_estimate_proxy_request(*, ctx, db, route_group, requested_model, payload, chain, allow_fallback, metrics_window):
        del ctx, db, payload, chain, allow_fallback, metrics_window
        provider = {
            "attempt_no": 1,
            "provider_code": "demo_provider",
            "provider_name": "Demo Provider",
            "model_code": requested_model,
            "billing_unit": "token",
            "priority": 100,
            "estimated_amount": "0.12",
            "estimated_power_amount": "1000.00",
            "currency": "CNY",
            "pricing_snapshot": {
                "request_factors": {
                    "input_tokens": 4,
                    "cached_input_tokens": 0,
                    "billable_input_tokens": 4,
                    "output_tokens": 1024,
                },
                "user_price": {
                    "currency": "CNY",
                    "input_per_1m_tokens": "19.44444443",
                    "cached_input_per_1m_tokens": "1.94444445",
                    "output_per_1m_tokens": "116.66666655",
                },
            },
            "metrics": {
                "window": "24h",
                "sample_count": 0,
                "success_count": 0,
                "success_rate": 0,
                "sample_ready": False,
                "latency": {
                    "avg_ms": None,
                    "p50_ms": None,
                    "p95_ms": None,
                    "sample_count": 0,
                },
            },
            "rank": 1,
            "recommended": True,
        }
        return {
            "route_group": route_group,
            "model": requested_model,
            "route_mode": "default",
            "chain": ["demo_provider"],
            "request_factors": provider["pricing_snapshot"]["request_factors"],
            "selected_provider": provider,
            "cheapest_provider": provider,
            "provider_options": [provider],
            "required_power_amount": "1000.00",
            "missing_power_amount": "0",
            "balance_check_basis": {
                "mode": "max_provider_in_route_plan",
                "provider_code": "demo_provider",
                "provider_name": "Demo Provider",
                "required_power_amount": "1000.00",
                "missing_power_amount": "0",
            },
            "actual_charge_basis": {
                "mode": "actual_success_provider",
                "description": "Final charge uses the provider that actually succeeds.",
            },
            "account": {
                "balance": "10000.00",
                "available_balance": "10000.00",
                "sufficient_balance": True,
                "status": "active",
            },
        }

    monkeypatch.setattr(estimates_route, "estimate_proxy_request", fake_estimate_proxy_request)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "gpt-5.4",
                "payload": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "hello",
                        }
                    ]
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["quote_mode"] == "estimated"
    assert response.json()["lowest_price"] == "0.00007777777772"
    assert response.json()["highest_price"] == "0.11954444432492"


def test_estimates_route_uses_async_estimator_for_vidu_model(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="vidu")
            if model_code == "viduq3-pro" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_task(
        self: AsyncTaskExecutionService,
        *,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, ctx
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
                "chain": chain,
                "fallback": fallback,
                "metrics_window": metrics_window,
            }
        )
        return _estimate_response(route_group=route_group, model=fixed_model_code)

    monkeypatch.setattr(AsyncTaskExecutionService, "estimate_task", fake_estimate_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "viduq3-pro",
                "payload": {
                    "mode": "image",
                    "images": ["https://example.com/frame.png"],
                    "duration": 5,
                    "resolution": "720p",
                    "audio": True,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="viduq3-pro", quote_mode="exact")
    assert captured == {
        "route_group": "vidu",
        "fixed_model_code": "viduq3-pro",
        "payload": {
            "mode": "image",
            "images": ["https://example.com/frame.png"],
            "duration": 5,
            "resolution": "720p",
            "audio": True,
        },
        "chain": None,
        "fallback": None,
        "metrics_window": None,
    }


def test_estimates_route_normalizes_qwen_system_tts_payload(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="qwen_tts")
            if model_code == "qwen3-tts-instruct-flash" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_proxy_request(*, ctx, db, route_group, requested_model, payload, chain, allow_fallback, metrics_window):
        del ctx, db, chain, allow_fallback, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "requested_model": requested_model,
                "payload": payload,
            }
        )
        return _estimate_response(route_group=route_group, model=str(requested_model))

    monkeypatch.setattr(estimates_route, "estimate_proxy_request", fake_estimate_proxy_request)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "qwen3-tts-instruct-flash",
                "payload": {
                    "text": "你好，欢迎使用 35m.ai。",
                    "voice": "Cherry",
                    "instructions": "更热情一点",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="qwen3-tts-instruct-flash", quote_mode="exact")
    assert captured == {
        "route_group": "qwen_tts",
        "requested_model": "qwen3-tts-instruct-flash",
        "payload": {
            "model": "qwen3-tts-instruct-flash",
            "input": {
                "text": "你好，欢迎使用 35m.ai。",
                "voice": "Cherry",
                "instructions": "更热情一点",
            },
        },
    }


def test_estimates_route_normalizes_minimax_tts_payload(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="minimax_t2a_async")
            if model_code == "speech-2.8-hd" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_task(
        self: AsyncTaskExecutionService,
        *,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, ctx, chain, fallback, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
            }
        )
        return _estimate_response(route_group=route_group, model=fixed_model_code)

    monkeypatch.setattr(AsyncTaskExecutionService, "estimate_task", fake_estimate_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "speech-2.8-hd",
                "payload": {
                    "text": "This is a long-form speech demo.",
                    "voice_id": "English_expressive_narrator",
                    "audio_setting": {
                        "format": "mp3",
                    },
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="speech-2.8-hd", quote_mode="exact")
    assert captured == {
        "route_group": "minimax_t2a_async",
        "fixed_model_code": "speech-2.8-hd",
        "payload": {
            "model": "speech-2.8-hd",
            "text": "This is a long-form speech demo.",
            "voice_setting": {
                "voice_id": "English_expressive_narrator",
            },
            "audio_setting": {
                "format": "mp3",
            },
        },
    }


def test_estimates_route_supports_minimax_turbo_tts(monkeypatch) -> None:
    from app.api.routes.models import estimates as estimates_route

    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: ApiKeyContext(user_id=9, api_key_id=3, key_name="demo")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    monkeypatch.setattr(
        estimates_route,
        "get_platform_config_snapshot",
        lambda: SimpleNamespace(
            get_primary_route=lambda model_code, public_only=True: SimpleNamespace(route_group="minimax_t2a_async")
            if model_code == "speech-2.8-turbo" and public_only
            else None
        ),
    )

    captured: dict[str, object] = {}

    def fake_estimate_task(
        self: AsyncTaskExecutionService,
        *,
        ctx,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, object],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, object]:
        del self, ctx, chain, fallback, metrics_window
        captured.update(
            {
                "route_group": route_group,
                "fixed_model_code": fixed_model_code,
                "payload": payload,
            }
        )
        return _estimate_response(route_group=route_group, model=fixed_model_code)

    monkeypatch.setattr(AsyncTaskExecutionService, "estimate_task", fake_estimate_task)

    with TestClient(app) as client:
        response = client.post(
            "/v1/estimates",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "speech-2.8-turbo",
                "payload": {
                    "text": "This is a turbo speech demo.",
                    "voice_id": "English_expressive_narrator",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == _public_estimate_summary(model="speech-2.8-turbo", quote_mode="exact")
    assert captured == {
        "route_group": "minimax_t2a_async",
        "fixed_model_code": "speech-2.8-turbo",
        "payload": {
            "model": "speech-2.8-turbo",
            "text": "This is a turbo speech demo.",
            "voice_setting": {
                "voice_id": "English_expressive_narrator",
            },
        },
    }
