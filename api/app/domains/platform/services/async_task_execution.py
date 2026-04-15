from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext
from app.core.pricing_catalog import quote_request
from app.core.provider_support import provider_supports_payload
from app.core.vidu_video import sanitize_vidu_payload_for_logging
from app.domains.platform.entities.entities import Task
from app.domains.platform.providers.registry import get_adapter
from app.domains.platform.services.billing import BillingService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.provider_account_runtime import ProviderAccountRuntimeService
from app.domains.platform.services.provider_request_log import ProviderRequestLogService
from app.domains.platform.services.provider_options import ProviderOptionsService
from app.domains.platform.services.request_log import RequestLogService
from app.domains.platform.services.routing import NoAvailableProviderError, ProviderNotFoundError, RoutingService
from app.domains.platform.services.task_control import TaskControlService

CreateInvokeBuilder = Callable[[Any, Any, dict[str, Any]], dict[str, Any]]
TaskInvokeBuilder = Callable[[Any, Task], dict[str, Any]]
TaskContentBuilder = Callable[[Any, Task], dict[str, Any]]
TaskResponseBuilder = Callable[[Task, dict[str, Any]], dict[str, Any]]


def extract_error_context(exc: Exception) -> tuple[int | None, str]:
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


def task_finished(status: str | None) -> bool:
    return status in {"completed", "failed", "cancelled", "canceled"}


def _build_logged_request_body(
    *,
    payload: dict[str, Any],
    requested_model: str | None,
    route_group: str,
) -> dict[str, Any]:
    logged_payload = sanitize_vidu_payload_for_logging(payload) if route_group == "vidu" else dict(payload)
    if not requested_model:
        return logged_payload
    if isinstance(logged_payload.get("model"), str) and logged_payload.get("model"):
        return logged_payload
    return {**logged_payload, "model": requested_model}


class AsyncTaskExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.routing_service = RoutingService()
        self.request_logger = RequestLogService(db)
        self.provider_request_logger = ProviderRequestLogService(db)
        self.billing_service = BillingService(db)
        self.task_control = TaskControlService(db)
        self.provider_options = ProviderOptionsService(db)
        self.provider_account_runtime = ProviderAccountRuntimeService(db)

    def _resolve_task_execution_model_code(self, *, task: Task, route_group: str) -> str:
        snapshot = get_platform_config_snapshot()
        for binding in snapshot.list_bindings(task.public_model_code, route_group):
            if binding.provider_code == task.provider_code:
                return binding.execution_model_code
        return task.public_model_code

    def plan_route(
        self,
        *,
        route_group: str,
        requested_model: str,
        chain: str | None,
        allow_fallback: bool,
    ):
        try:
            return self.routing_service.plan(
                route_group=route_group,
                requested_model=requested_model,
                chain=chain,
                allow_fallback=allow_fallback,
            )
        except ProviderNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NoAvailableProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    def _resolve_effective_chain(
        self,
        *,
        route_group: str,
        requested_model: str,
        chain: str | None,
        allow_fallback: bool,
    ) -> str | None:
        if chain:
            return chain
        return self.routing_service.default_chain(
            route_group=route_group,
            requested_model=requested_model,
            allow_fallback=allow_fallback,
        )

    def _build_provider_options(
        self,
        *,
        route_group: str,
        public_model_code: str,
        request_payload: dict[str, Any],
        attempts: list[Any],
        metrics_window: str,
        ) -> list[dict[str, Any]]:
        return self.provider_options.build_provider_options(
            route_group=route_group,
            public_model_code=public_model_code,
            request_payload=request_payload,
            attempts=attempts,
            provider_lookup=self.routing_service.get_provider,
            window=metrics_window,
        )

    def _filter_attempts_for_payload(
        self,
        *,
        route_group: str,
        model_code: str,
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

    def _get_balance_check_basis(self, provider_options: list[dict[str, Any]]) -> dict[str, Any]:
        if not provider_options:
            raise HTTPException(status_code=503, detail="no_available_provider")
        return max(
            provider_options,
            key=lambda item: Decimal(str(item.get("estimated_power_amount") or "0")),
        )

    def _get_cheapest_provider(self, provider_options: list[dict[str, Any]]) -> dict[str, Any]:
        if not provider_options:
            raise HTTPException(status_code=503, detail="no_available_provider")
        return min(
            provider_options,
            key=lambda item: (
                Decimal(str(item.get("estimated_power_amount") or "0")),
                Decimal(str(item.get("estimated_amount") or "0")),
            ),
        )

    def estimate_task(
        self,
        *,
        ctx: ApiKeyContext,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, Any],
        chain: str | None,
        fallback: bool | None,
        metrics_window: str | None = None,
    ) -> dict[str, Any]:
        allow_fallback = True if fallback is None else fallback
        request_payload = {k: v for k, v in payload.items() if k != "model"}
        request_payload["model"] = fixed_model_code
        effective_chain = self._resolve_effective_chain(
            route_group=route_group,
            requested_model=fixed_model_code,
            chain=chain,
            allow_fallback=allow_fallback,
        )

        route_plan = self.plan_route(
            route_group=route_group,
            requested_model=fixed_model_code,
            chain=effective_chain,
            allow_fallback=allow_fallback,
        )
        route_plan.attempts = self._filter_attempts_for_payload(
            route_group=route_group,
            model_code=fixed_model_code,
            payload=request_payload,
            attempts=route_plan.attempts,
        )
        route_plan.attempts = self.provider_account_runtime.expand_attempts(
            user_id=ctx.user_id,
            attempts=route_plan.attempts,
        )

        provider_options = self._build_provider_options(
            route_group=route_group,
            public_model_code=fixed_model_code,
            request_payload=request_payload,
            attempts=route_plan.attempts,
            metrics_window=metrics_window or "24h",
        )
        selected_provider = provider_options[0]
        cheapest_provider = self._get_cheapest_provider(provider_options)
        balance_check_basis = self._get_balance_check_basis(provider_options)
        account = self.task_control.ensure_active_account(ctx.user_id)
        available_balance = Decimal(account.balance)
        required_power = Decimal(str(balance_check_basis["estimated_power_amount"] or "0"))
        sufficient_balance = available_balance >= required_power
        missing_power = max(Decimal("0"), required_power - available_balance)

        return {
            "route_group": route_group,
            "model": fixed_model_code,
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
                "description": "Final charge uses the power amount of the provider that actually succeeds.",
            },
            "account": {
                "balance": str(account.balance),
                "available_balance": str(available_balance),
                "sufficient_balance": sufficient_balance,
                "status": account.status,
            },
        }

    async def create_task(
        self,
        *,
        http_request: Request,
        ctx: ApiKeyContext,
        route_group: str,
        fixed_model_code: str,
        payload: dict[str, Any],
        forward_payload: dict[str, Any] | None = None,
        chain: str | None,
        fallback: bool | None,
        create_invoke_builder: CreateInvokeBuilder,
        response_builder: TaskResponseBuilder,
        metrics_window: str | None = None,
    ) -> dict[str, Any]:
        allow_fallback = True if fallback is None else fallback
        effective_forward_payload = forward_payload if forward_payload is not None else dict(payload)
        request_payload = {k: v for k, v in payload.items() if k != "model"}
        request_payload["model"] = fixed_model_code
        effective_chain = self._resolve_effective_chain(
            route_group=route_group,
            requested_model=fixed_model_code,
            chain=chain,
            allow_fallback=allow_fallback,
        )

        self.task_control.ensure_active_account(ctx.user_id)

        route_plan = self.plan_route(
            route_group=route_group,
            requested_model=fixed_model_code,
            chain=effective_chain,
            allow_fallback=allow_fallback,
        )
        route_plan.attempts = self._filter_attempts_for_payload(
            route_group=route_group,
            model_code=fixed_model_code,
            payload=request_payload,
            attempts=route_plan.attempts,
        )
        route_plan.attempts = self.provider_account_runtime.expand_attempts(
            user_id=ctx.user_id,
            attempts=route_plan.attempts,
        )
        provider_options = self._build_provider_options(
            route_group=route_group,
            public_model_code=fixed_model_code,
            request_payload=request_payload,
            attempts=route_plan.attempts,
            metrics_window=metrics_window or "24h",
        )
        request_log = self.request_logger.create(
            request_id=http_request.state.request_id,
            route_mode=route_plan.route_mode,
            route_plan=route_plan.route_plan,
            user_id=ctx.user_id,
            api_key_id=ctx.api_key_id,
            fallback_enabled=allow_fallback,
            record_model_metrics=True,
            public_model_code=fixed_model_code,
            route_group=route_group,
            request_path=str(http_request.url.path),
            request_headers={
                "x-api35-chain": effective_chain,
                "x-api35-fallback": str(allow_fallback).lower(),
            },
            request_body=_build_logged_request_body(
                payload=request_payload,
                requested_model=fixed_model_code,
                route_group=route_group,
            ),
        )

        attempt_errors: list[dict[str, Any]] = []
        fallback_reason: str | None = None

        for attempt_no, route_result in enumerate(route_plan.attempts, start=1):
            provider = route_result.provider or self.routing_service.get_provider(route_result.provider_code)
            model_snapshot = get_platform_config_snapshot().get_model(route_result.public_model_code)
            amount, currency, billing_snapshot = quote_request(
                provider_code=route_result.provider_code,
                route_group=route_group,
                execution_model_code=route_result.execution_model_code,
                pricing_strategy=route_result.pricing_strategy,
                public_model_code=route_result.public_model_code,
                payload=request_payload,
            )
            provider_request = self.provider_request_logger.create(
                request_row_id=request_log.id,
                attempt_no=attempt_no,
                provider_code=route_result.provider_code,
                provider_account_id=route_result.provider_account_id,
                provider_account_short_id=route_result.provider_account_short_id,
                provider_account_owner_type=route_result.provider_account_owner_type,
                execution_model_code=route_result.execution_model_code,
                fallback_reason=fallback_reason,
                request_payload=sanitize_vidu_payload_for_logging(request_payload) if route_group == "vidu" else request_payload,
            )

            try:
                adapter = get_adapter(provider.adapter_key)
                invoke_ctx = create_invoke_builder(provider, route_result, request_payload)
                invoke_ctx.setdefault("public_path", str(http_request.url.path))
                invoke_ctx.setdefault("public_method", http_request.method)
                invoke_ctx["forward_payload"] = effective_forward_payload
                result = await adapter.invoke(invoke_ctx)
            except HTTPException as exc:
                http_status_code = exc.status_code
                error_message = str(exc.detail)
                self.provider_request_logger.finish(
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
            except (httpx.HTTPError, KeyError) as exc:
                http_status_code, error_message = extract_error_context(exc)
                self.provider_request_logger.finish(
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

            provider_task_id = result.get("id") if isinstance(result, dict) else None
            self.provider_request_logger.finish(
                provider_request,
                status="succeeded",
                response_payload=result if isinstance(result, dict) else {"data": result},
                provider_request_id=provider_task_id,
            )

            task_status = result.get("status", "submitted") if isinstance(result, dict) else "submitted"
            initial_result_payload = result if isinstance(result, dict) else {"data": result}
            preserve_initial_result = task_finished(task_status) or route_group == "wan_video" or provider.adapter_key == "fal"
            task = Task(
                platform_task_id=f"task_{uuid.uuid4().hex[:24]}",
                request_id=request_log.id,
                provider_code=route_result.provider_code,
                provider_account_id=route_result.provider_account_id,
                provider_account_short_id=route_result.provider_account_short_id,
                provider_account_owner_type=route_result.provider_account_owner_type,
                public_model_code=route_result.public_model_code,
                provider_task_id=provider_task_id,
                status=task_status,
                result_payload=initial_result_payload if preserve_initial_result else None,
                last_polled_at=None,
                finished_at=datetime.now(timezone.utc) if task_finished(task_status) else None,
            )
            self.db.add(task)
            if task_finished(task_status):
                from app.domains.platform.services.model_metrics_rollup import ModelMetricsRollupService

                ModelMetricsRollupService(self.db).record_task_result(task, route_group=route_group, finished_at=task.finished_at)
            self.db.commit()
            self.db.refresh(task)

            self.billing_service.record_async_pending(
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
                billing_snapshot=billing_snapshot,
            )
            if task_finished(task_status):
                self.billing_service.finalize_async(
                    request_id=request_log.id,
                    final_status="succeeded" if task_status == "completed" else "waived",
                    billing_snapshot={"provider_status": task_status},
                )

            response_body = response_builder(task, result if isinstance(result, dict) else {"data": result})
            self.request_logger.finish(request_log, status="succeeded", response_body=response_body)
            return response_body

        self.request_logger.finish(
            request_log,
            status="failed",
            response_body={"error": "provider_call_failed", "attempts": attempt_errors},
        )
        raise HTTPException(
            status_code=502,
            detail={"error": "provider_call_failed", "attempts": attempt_errors},
        )

    async def get_task(
        self,
        *,
        http_request: Request,
        ctx: ApiKeyContext,
        task: Task,
        route_group: str,
        task_invoke_builder: TaskInvokeBuilder,
        response_builder: TaskResponseBuilder,
    ) -> dict[str, Any]:
        if task_finished(task.status) and task.result_payload is not None:
            request_log = self.request_logger.create(
                request_id=http_request.state.request_id,
                route_mode="task_lookup_cache",
                route_plan=[task.provider_code],
                user_id=ctx.user_id,
                api_key_id=ctx.api_key_id,
                fallback_enabled=False,
                record_model_metrics=False,
                public_model_code=task.public_model_code,
                route_group=route_group,
                request_path=str(http_request.url.path),
                request_headers={},
                request_body={},
            )
            response_body = response_builder(task, task.result_payload)
            self.request_logger.finish(request_log, status="succeeded", response_body=response_body)
            return response_body

        provider = self.provider_account_runtime.resolve_provider(
            provider_code=task.provider_code,
            provider_account_id=task.provider_account_id,
        )
        request_log = self.request_logger.create(
            request_id=http_request.state.request_id,
            route_mode="task_lookup",
            route_plan=[task.provider_code],
            user_id=ctx.user_id,
            api_key_id=ctx.api_key_id,
            fallback_enabled=False,
            record_model_metrics=False,
            public_model_code=task.public_model_code,
            route_group=route_group,
            request_path=str(http_request.url.path),
            request_headers={},
            request_body={},
        )
        provider_request = self.provider_request_logger.create(
            request_row_id=request_log.id,
            attempt_no=1,
            provider_code=task.provider_code,
            provider_account_id=task.provider_account_id,
            provider_account_short_id=task.provider_account_short_id,
            provider_account_owner_type=task.provider_account_owner_type,
            execution_model_code=self._resolve_task_execution_model_code(task=task, route_group=route_group),
            fallback_reason=None,
            request_payload={},
        )

        try:
            adapter = get_adapter(provider.adapter_key)
            invoke_ctx = task_invoke_builder(provider, task)
            invoke_ctx.setdefault("public_path", str(http_request.url.path))
            invoke_ctx.setdefault("public_method", http_request.method)
            result = await adapter.invoke(invoke_ctx)
        except (httpx.HTTPError, KeyError) as exc:
            http_status_code, error_message = extract_error_context(exc)
            self.provider_request_logger.finish(
                provider_request,
                status="failed",
                response_payload={"error": error_message},
                provider_request_id=task.provider_task_id,
                http_status_code=http_status_code,
                error_message=error_message,
            )
            self.request_logger.finish(request_log, status="failed", response_body={"error": error_message})
            raise HTTPException(status_code=502, detail=error_message) from exc

        previous_status = task.status
        task.status = result.get("status", task.status) if isinstance(result, dict) else task.status
        if task_finished(task.status):
            task.result_payload = result if isinstance(result, dict) else {"data": result}
            task.finished_at = datetime.now(timezone.utc)
            from app.domains.platform.services.model_metrics_rollup import ModelMetricsRollupService

            ModelMetricsRollupService(self.db).record_task_result(task, route_group=route_group, finished_at=task.finished_at)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        if not task_finished(previous_status) and task_finished(task.status):
            self.billing_service.finalize_async(
                request_id=task.request_id,
                final_status="succeeded" if task.status == "completed" else "waived",
                billing_snapshot={"provider_status": task.status},
            )

        self.provider_request_logger.finish(
            provider_request,
            status="succeeded",
            response_payload=result if isinstance(result, dict) else {"data": result},
            provider_request_id=task.provider_task_id,
        )
        response_body = response_builder(task, result if isinstance(result, dict) else {"data": result})
        self.request_logger.finish(request_log, status="succeeded", response_body=response_body)
        return response_body

    async def download_content(
        self,
        *,
        http_request: Request,
        ctx: ApiKeyContext,
        task: Task,
        route_group: str,
        task_content_builder: TaskContentBuilder,
    ) -> Response:
        provider = self.provider_account_runtime.resolve_provider(
            provider_code=task.provider_code,
            provider_account_id=task.provider_account_id,
        )
        request_log = self.request_logger.create(
            request_id=http_request.state.request_id,
            route_mode="task_lookup",
            route_plan=[task.provider_code],
            user_id=ctx.user_id,
            api_key_id=ctx.api_key_id,
            fallback_enabled=False,
            record_model_metrics=False,
            public_model_code=task.public_model_code,
            route_group=route_group,
            request_path=str(http_request.url.path),
            request_headers={},
            request_body={},
        )
        provider_request = self.provider_request_logger.create(
            request_row_id=request_log.id,
            attempt_no=1,
            provider_code=task.provider_code,
            provider_account_id=task.provider_account_id,
            provider_account_short_id=task.provider_account_short_id,
            provider_account_owner_type=task.provider_account_owner_type,
            execution_model_code=self._resolve_task_execution_model_code(task=task, route_group=route_group),
            fallback_reason=None,
            request_payload={},
        )

        try:
            adapter = get_adapter(provider.adapter_key)
            content_ctx = task_content_builder(provider, task)
            content_ctx.setdefault("public_path", str(http_request.url.path))
            content_ctx.setdefault("public_method", http_request.method)
            content, content_type = await adapter.fetch_content(content_ctx)
        except (httpx.HTTPError, KeyError, NotImplementedError) as exc:
            http_status_code, error_message = extract_error_context(exc)
            self.provider_request_logger.finish(
                provider_request,
                status="failed",
                response_payload={"error": error_message},
                provider_request_id=task.provider_task_id,
                http_status_code=http_status_code,
                error_message=error_message,
            )
            self.request_logger.finish(request_log, status="failed", response_body={"error": error_message})
            raise HTTPException(status_code=502, detail=error_message) from exc

        response_payload = {"content_type": content_type, "size": len(content)}
        self.provider_request_logger.finish(
            provider_request,
            status="succeeded",
            response_payload=response_payload,
            provider_request_id=task.provider_task_id,
        )
        self.request_logger.finish(request_log, status="succeeded", response_body=response_payload)
        return Response(content=content, media_type=content_type or "application/octet-stream")
