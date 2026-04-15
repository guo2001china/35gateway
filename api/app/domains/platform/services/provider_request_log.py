from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import ProviderRequest
from app.domains.platform.services.provider_metrics_rollup import ProviderMetricsRollupService


class ProviderRequestLogService:
    def __init__(self, db: Session):
        self.db = db
        self.rollup_service = ProviderMetricsRollupService(db)

    def create(
        self,
        *,
        request_row_id: int,
        attempt_no: int,
        provider_code: str,
        provider_account_id: int | None,
        provider_account_short_id: str | None,
        provider_account_owner_type: str | None,
        execution_model_code: str,
        fallback_reason: str | None,
        request_payload: dict[str, Any],
    ) -> ProviderRequest:
        row = ProviderRequest(
            request_id=request_row_id,
            attempt_no=attempt_no,
            provider_code=provider_code,
            provider_account_id=provider_account_id,
            provider_account_short_id=provider_account_short_id,
            provider_account_owner_type=provider_account_owner_type,
            execution_model_code=execution_model_code,
            fallback_reason=fallback_reason,
            request_payload=request_payload,
            status="started",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def finish(
        self,
        row: ProviderRequest,
        *,
        status: str,
        response_payload: dict[str, Any] | None,
        provider_request_id: str | None = None,
        http_status_code: int | None = None,
        error_message: str | None = None,
    ) -> ProviderRequest:
        ended_at = datetime.now(timezone.utc)
        started_at = row.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        row.status = status
        row.response_payload = response_payload
        row.provider_request_id = provider_request_id
        row.http_status_code = http_status_code
        row.error_message = error_message
        row.ended_at = ended_at
        row.duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        self.rollup_service.record_result(
            provider_code=row.provider_code,
            execution_model_code=row.execution_model_code,
            status=status,
            duration_ms=row.duration_ms,
            error_message=error_message,
            ended_at=ended_at,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
