from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, UserAccessContext
from app.core.pricing.quote import finalize_billing_snapshot
from app.core.pricing_catalog import quote_request
from app.core.provider_catalog import get_provider
from app.core.provider_catalog.types import ProviderConfig
from app.domains.platform.providers.registry import get_adapter
from app.domains.platform.services.billing import BillingService
from app.domains.platform.services.platform_config_snapshot import (
    PlatformModelProviderBindingSnapshot,
    get_platform_config_snapshot,
)
from app.domains.platform.services.provider_request_log import ProviderRequestLogService
from app.domains.platform.services.request_log import RequestLogService
from app.domains.platform.services.task_control import TaskControlService

logger = logging.getLogger(__name__)


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


def _extract_provider_request_id(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None
    for field in ("request_id", "id"):
        value = result.get(field)
        if isinstance(value, str) and value:
            return value
    return None


class ProviderApiExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.request_logger = RequestLogService(db)
        self.provider_request_logger = ProviderRequestLogService(db)
        self.billing_service = BillingService(db)
        self.task_control = TaskControlService(db)

    def _require_provider(self, provider_code: str) -> ProviderConfig:
        try:
            return get_provider(provider_code)
        except KeyError as exc:
            raise HTTPException(status_code=503, detail="provider_not_configured") from exc

    def _resolve_provider_model(
        self,
        *,
        provider_code: str,
        route_group: str,
        model_code: str,
    ) -> PlatformModelProviderBindingSnapshot:
        snapshot = get_platform_config_snapshot()
        for provider_model in snapshot.list_bindings(model_code, route_group):
            if provider_model.provider_code == provider_code:
                return provider_model
        raise HTTPException(status_code=404, detail="model_not_found")

    async def execute(
        self,
        *,
        http_request: Request,
        ctx: ApiKeyContext | UserAccessContext,
        provider_code: str,
        route_group: str,
        model_code: str,
        provider_path: str,
        payload: dict[str, Any],
        forward_payload: dict[str, Any] | None = None,
        method: str = "POST",
        bill_on_success: bool = False,
        persist_request_log: bool = True,
    ) -> dict[str, Any]:
        provider = self._require_provider(provider_code)
        provider_model = self._resolve_provider_model(
            provider_code=provider.provider_code,
            route_group=route_group,
            model_code=model_code,
        )
        model_snapshot = get_platform_config_snapshot().get_model(model_code)
        if bill_on_success:
            self.task_control.ensure_active_account(ctx.user_id)
            _, _, billing_snapshot = quote_request(
                provider_code=provider.provider_code,
                route_group=route_group,
                execution_model_code=provider_model.execution_model_code,
                pricing_strategy=provider_model.pricing_strategy,
                public_model_code=model_code,
                payload=payload,
            )
        else:
            self.task_control.ensure_active_account(ctx.user_id)
            billing_snapshot = None

        request_log = None
        provider_request = None
        request_id = getattr(http_request.state, "request_id", None)
        request_path = str(http_request.url.path)
        if persist_request_log:
            request_log = self.request_logger.create(
                request_id=request_id,
                route_mode="direct",
                route_plan=[provider.provider_code],
                user_id=ctx.user_id,
                api_key_id=ctx.api_key_id,
                fallback_enabled=False,
                record_model_metrics=bill_on_success,
                public_model_code=model_code,
                route_group=route_group,
                request_path=request_path,
                request_headers={},
                request_body=payload,
            )
            provider_request = self.provider_request_logger.create(
                request_row_id=request_log.id,
                attempt_no=1,
                provider_code=provider.provider_code,
                provider_account_id=None,
                provider_account_short_id=None,
                provider_account_owner_type=None,
                execution_model_code=provider_model.execution_model_code,
                fallback_reason=None,
                request_payload=payload,
            )

        try:
            adapter = get_adapter(provider.adapter_key)
            result = await adapter.invoke(
                {
                    "provider": provider,
                    "provider_model": provider_model,
                    "path": provider_path,
                    "payload": payload,
                    "forward_payload": forward_payload,
                    "method": method,
                    "public_path": request_path,
                    "public_method": http_request.method,
                    "public_model": model_code,
                }
            )
        except (httpx.HTTPError, KeyError) as exc:
            http_status_code, error_message = _extract_error_context(exc)
            response_payload = {"error": error_message}
            if persist_request_log and provider_request is not None and request_log is not None:
                self.provider_request_logger.finish(
                    provider_request,
                    status="failed",
                    response_payload=response_payload,
                    http_status_code=http_status_code,
                    error_message=error_message,
                )
                self.request_logger.finish(
                    request_log,
                    status="failed",
                    response_body=response_payload,
                )
            else:
                logger.warning(
                    "provider metadata request failed request_id=%s user_id=%s provider_code=%s route_group=%s model_code=%s path=%s error=%s",
                    request_id,
                    ctx.user_id,
                    provider.provider_code,
                    route_group,
                    model_code,
                    request_path,
                    error_message,
                )
            raise HTTPException(status_code=http_status_code or 502, detail=error_message) from exc

        response_payload = result if isinstance(result, dict) else {"data": result}
        if persist_request_log and provider_request is not None and request_log is not None:
            self.provider_request_logger.finish(
                provider_request,
                status="succeeded",
                response_payload=response_payload,
                provider_request_id=_extract_provider_request_id(result),
            )
        else:
            logger.info(
                "provider metadata request succeeded request_id=%s user_id=%s provider_code=%s route_group=%s model_code=%s path=%s",
                request_id,
                ctx.user_id,
                provider.provider_code,
                route_group,
                model_code,
                request_path,
            )
        if bill_on_success and billing_snapshot is not None and request_log is not None:
            final_billing_snapshot = finalize_billing_snapshot(
                provider_code=provider.provider_code,
                route_group=route_group,
                execution_model_code=provider_model.execution_model_code,
                pricing_strategy=provider_model.pricing_strategy,
                public_model_code=model_code,
                response_payload=response_payload,
                estimated_snapshot=billing_snapshot,
            )
            self.billing_service.record_sync_success(
                request_id=request_log.id,
                user_id=ctx.user_id,
                api_key_id=ctx.api_key_id,
                provider_code=provider.provider_code,
                provider_account_id=None,
                provider_account_short_id=None,
                provider_account_owner_type=None,
                public_model_code=model_code,
                route_group=route_group,
                billing_unit=model_snapshot.billing_unit,
                billing_snapshot=final_billing_snapshot,
            )
        if persist_request_log and request_log is not None:
            self.request_logger.finish(
                request_log,
                status="succeeded",
                response_body=response_payload,
            )
        return response_payload
