from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext
from app.core.pricing.quote import finalize_billing_snapshot
from app.core.provider_support import provider_supports_payload
from app.domains.platform.providers.registry import get_adapter
from app.domains.platform.services.billing import BillingService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.provider_account_runtime import ProviderAccountRuntimeService
from app.domains.platform.services.provider_request_log import ProviderRequestLogService
from app.domains.platform.services.provider_options import ProviderOptionsService
from app.domains.platform.services.request_log import RequestLogService
from app.domains.platform.services.routing import NoAvailableProviderError, ProviderNotFoundError, RoutingService
from app.domains.platform.services.task_control import TaskControlService


def _extract_error_context(exc: Exception) -> tuple[int | None, str]:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        try:
            payload = exc.response.json()
            if isinstance(payload, dict):
                error_detail = payload.get("error", payload)
            else:
                error_detail = payload
            return status_code, str(error_detail)
        except ValueError:
            return status_code, exc.response.text or str(exc)

    if isinstance(exc, httpx.HTTPError):
        return None, str(exc) or exc.__class__.__name__

    return None, str(exc) or exc.__class__.__name__


def _filter_attempts_for_payload(
    *,
    route_group: str,
    payload: dict[str, Any],
    attempts: list[Any],
) -> list[Any]:
    filtered = [
        attempt
        for attempt in attempts
        if provider_supports_payload(
            route_group=route_group,
            provider_code=attempt.provider_code,
            model_code=attempt.execution_model_code,
            payload=payload,
        )
    ]
    if not filtered:
        raise HTTPException(status_code=503, detail="no_available_provider_for_input_mode")
    return filtered


def _get_balance_check_basis(provider_options: list[dict[str, Any]]) -> dict[str, Any]:
    if not provider_options:
        raise HTTPException(status_code=503, detail="no_available_provider")
    return max(
        provider_options,
        key=lambda item: Decimal(str(item.get("estimated_power_amount") or "0")),
    )


def _get_cheapest_provider(provider_options: list[dict[str, Any]]) -> dict[str, Any]:
    if not provider_options:
        raise HTTPException(status_code=503, detail="no_available_provider")
    return min(
        provider_options,
        key=lambda item: (
            Decimal(str(item.get("estimated_power_amount") or "0")),
            Decimal(str(item.get("estimated_amount") or "0")),
        ),
    )


def _resolve_effective_chain(
    *,
    routing_service: RoutingService,
    route_group: str,
    requested_model: str | None,
    chain: str | None,
    allow_fallback: bool,
) -> str | None:
    if chain:
        return chain
    return routing_service.default_chain(
        route_group=route_group,
        requested_model=requested_model,
        allow_fallback=allow_fallback,
    )


def _build_logged_request_body(
    *,
    payload: dict[str, Any],
    requested_model: str | None,
) -> dict[str, Any]:
    if not requested_model:
        return payload
    if isinstance(payload.get("model"), str) and payload.get("model"):
        return payload
    return {**payload, "model": requested_model}


def estimate_proxy_request(
    *,
    ctx: ApiKeyContext,
    db: Session,
    route_group: str,
    requested_model: str | None,
    payload: dict[str, Any],
    chain: str | None,
    allow_fallback: bool,
    metrics_window: str | None = None,
) -> dict[str, Any]:
    routing_service = RoutingService()
    task_control = TaskControlService(db)
    provider_options_service = ProviderOptionsService(db)
    provider_account_runtime = ProviderAccountRuntimeService(db)
    effective_chain = _resolve_effective_chain(
        routing_service=routing_service,
        route_group=route_group,
        requested_model=requested_model,
        chain=chain,
        allow_fallback=allow_fallback,
    )

    try:
        route_plan = routing_service.plan(
            route_group=route_group,
            requested_model=requested_model,
            chain=effective_chain,
            allow_fallback=allow_fallback,
        )
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoAvailableProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    route_plan.attempts = _filter_attempts_for_payload(
        route_group=route_group,
        payload=payload,
        attempts=route_plan.attempts,
    )
    route_plan.attempts = provider_account_runtime.expand_attempts(
        user_id=ctx.user_id,
        attempts=route_plan.attempts,
    )

    provider_options = provider_options_service.build_provider_options(
        route_group=route_group,
        public_model_code=requested_model or route_plan.attempts[0].public_model_code,
        request_payload=payload,
        attempts=route_plan.attempts,
        provider_lookup=routing_service.get_provider,
        window=metrics_window or "24h",
    )

    selected_provider = provider_options[0]
    cheapest_provider = _get_cheapest_provider(provider_options)
    balance_check_basis = _get_balance_check_basis(provider_options)
    account = task_control.ensure_active_account(ctx.user_id)
    available_balance = Decimal(account.balance)
    required_power = Decimal(str(balance_check_basis["estimated_power_amount"] or "0"))
    sufficient_balance = available_balance >= required_power
    missing_power = max(Decimal("0"), required_power - available_balance)

    return {
        "route_group": route_group,
        "model": requested_model,
        "route_mode": route_plan.route_mode,
        "chain": route_plan.route_plan,
        "request_factors": selected_provider["pricing_snapshot"].get("request_factors", {}),
        "selected_provider": selected_provider,
        "cheapest_provider": cheapest_provider,
        "provider_options": provider_options,
        "required_power_amount": str(required_power),
        "missing_power_amount": str(missing_power),
        "balance_check_basis": {
            "mode": "max_provider_in_route_plan",
            "provider_code": balance_check_basis["provider_code"],
            "provider_name": balance_check_basis["provider_name"],
            "required_power_amount": balance_check_basis["estimated_power_amount"],
            "missing_power_amount": str(missing_power),
        },
        "actual_charge_basis": {
            "mode": "actual_success_provider",
            "description": "Final charge uses the provider that actually succeeds.",
        },
        "account": {
            "balance": str(account.balance),
            "available_balance": str(available_balance),
            "sufficient_balance": sufficient_balance,
            "status": account.status,
        },
    }


async def execute_proxy_request(
    *,
    http_request: Request,
    ctx: ApiKeyContext,
    db: Session,
    route_group: str,
    requested_model: str | None,
    provider_path: str,
    payload: dict[str, Any],
    chain: str | None,
    allow_fallback: bool,
) -> Any:
    routing_service = RoutingService()
    request_logger = RequestLogService(db)
    provider_request_logger = ProviderRequestLogService(db)
    billing_service = BillingService(db)
    task_control = TaskControlService(db)
    provider_options_service = ProviderOptionsService(db)
    provider_account_runtime = ProviderAccountRuntimeService(db)
    effective_chain = _resolve_effective_chain(
        routing_service=routing_service,
        route_group=route_group,
        requested_model=requested_model,
        chain=chain,
        allow_fallback=allow_fallback,
    )

    task_control.ensure_active_account(ctx.user_id)

    try:
        route_plan = routing_service.plan(
            route_group=route_group,
            requested_model=requested_model,
            chain=effective_chain,
            allow_fallback=allow_fallback,
        )
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoAvailableProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    route_plan.attempts = _filter_attempts_for_payload(
        route_group=route_group,
        payload=payload,
        attempts=route_plan.attempts,
    )
    route_plan.attempts = provider_account_runtime.expand_attempts(
        user_id=ctx.user_id,
        attempts=route_plan.attempts,
    )

    ranked_options = provider_options_service.build_provider_options(
        route_group=route_group,
        public_model_code=requested_model or route_plan.attempts[0].public_model_code,
        request_payload=payload,
        attempts=route_plan.attempts,
        provider_lookup=routing_service.get_provider,
        window="24h",
    )
    route_estimates = [
        {
            "attempt_no": option["attempt_no"],
            "provider_code": option["provider_code"],
            "execution_model_code": option["execution_model_code"],
            "pricing_strategy": option["pricing_strategy"],
            "amount": Decimal(option["estimated_amount"]),
            "currency": option["currency"],
            "billing_snapshot": option["pricing_snapshot"],
            "power_amount": Decimal(str(option["estimated_power_amount"] or "0")),
        }
        for option in ranked_options
    ]

    request_log = request_logger.create(
        request_id=http_request.state.request_id,
        route_mode=route_plan.route_mode,
        route_plan=route_plan.route_plan,
        user_id=ctx.user_id,
        api_key_id=ctx.api_key_id,
        fallback_enabled=allow_fallback,
        record_model_metrics=True,
        public_model_code=requested_model or route_plan.attempts[0].public_model_code,
        route_group=route_group,
        request_path=str(http_request.url.path),
        request_headers={
            "x-api35-chain": effective_chain,
            "x-api35-fallback": str(allow_fallback).lower(),
        },
        request_body=_build_logged_request_body(payload=payload, requested_model=requested_model),
    )

    attempt_errors: list[dict[str, Any]] = []
    fallback_reason: str | None = None

    for attempt_no, route_result in enumerate(route_plan.attempts, start=1):
        provider = route_result.provider or routing_service.get_provider(route_result.provider_code)
        model_snapshot = get_platform_config_snapshot().get_model(route_result.public_model_code)
        estimate = route_estimates[attempt_no - 1]

        provider_request = provider_request_logger.create(
            request_row_id=request_log.id,
            attempt_no=attempt_no,
            provider_code=route_result.provider_code,
            provider_account_id=route_result.provider_account_id,
            provider_account_short_id=route_result.provider_account_short_id,
            provider_account_owner_type=route_result.provider_account_owner_type,
            execution_model_code=route_result.execution_model_code,
            fallback_reason=fallback_reason,
            request_payload=payload,
        )

        try:
            adapter = get_adapter(provider.adapter_key)
            result = await adapter.invoke(
                {
                    "provider": provider,
                    "provider_model": route_result,
                    "path": provider_path,
                    "payload": payload,
                    "public_path": str(http_request.url.path),
                    "public_method": http_request.method,
                }
            )
        except (httpx.HTTPError, KeyError) as exc:
            http_status_code, error_message = _extract_error_context(exc)
            provider_request_logger.finish(
                provider_request,
                status="failed",
                response_payload={"error": error_message},
                http_status_code=http_status_code,
                error_message=error_message,
            )
            attempt_errors.append(
                {
                    "attempt_no": attempt_no,
                    "provider_code": provider.provider_code,
                    "provider_account_short_id": route_result.provider_account_short_id,
                    "http_status_code": http_status_code,
                    "error": error_message,
                }
            )
            fallback_reason = error_message
            continue

        provider_request_id = result.get("id") if isinstance(result, dict) else None
        provider_request_logger.finish(
            provider_request,
            status="succeeded",
            response_payload=result if isinstance(result, dict) else {"data": result},
            provider_request_id=provider_request_id,
        )
        final_billing_snapshot = finalize_billing_snapshot(
            provider_code=route_result.provider_code,
            route_group=route_group,
            execution_model_code=route_result.execution_model_code,
            pricing_strategy=route_result.pricing_strategy,
            public_model_code=route_result.public_model_code,
            response_payload=result if isinstance(result, dict) else {"data": result},
            estimated_snapshot=estimate["billing_snapshot"],
        )
        billing_service.record_sync_success(
            request_id=request_log.id,
            user_id=ctx.user_id,
            api_key_id=ctx.api_key_id,
            provider_code=route_result.provider_code,
            provider_account_id=route_result.provider_account_id,
            provider_account_short_id=route_result.provider_account_short_id,
            provider_account_owner_type=route_result.provider_account_owner_type,
            public_model_code=route_result.public_model_code,
            route_group=route_group,
            billing_unit=model_snapshot.billing_unit,
            billing_snapshot=final_billing_snapshot,
        )
        request_logger.finish(
            request_log,
            status="succeeded",
            response_body=result if isinstance(result, dict) else {"data": result},
        )
        return result

    request_logger.finish(
        request_log,
        status="failed",
        response_body={"error": "provider_call_failed", "attempts": attempt_errors},
    )
    raise HTTPException(
        status_code=502,
        detail={"error": "provider_call_failed", "attempts": attempt_errors},
    )
