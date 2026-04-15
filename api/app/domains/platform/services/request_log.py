from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import Request
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.model_metrics_rollup import ModelMetricsRollupService


class RequestLogService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        request_id: str,
        route_mode: str,
        route_plan: list[str],
        user_id: int,
        api_key_id: int,
        fallback_enabled: bool,
        record_model_metrics: bool,
        public_model_code: str | None,
        route_group: str,
        request_path: str,
        request_headers: dict[str, Any],
        request_body: dict[str, Any],
    ) -> Request:
        request_log = Request(
            request_id=request_id,
            route_mode=route_mode,
            route_plan=route_plan,
            user_id=user_id,
            api_key_id=api_key_id,
            fallback_enabled=fallback_enabled,
            record_model_metrics=record_model_metrics,
            public_model_code=public_model_code,
            route_group=route_group,
            request_path=request_path,
            request_headers=request_headers,
            request_body=request_body,
            status="started",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(request_log)
        self.db.commit()
        self.db.refresh(request_log)
        return request_log

    def finish(self, request_log: Request, *, status: str, response_body: dict[str, Any]) -> Request:
        ended_at = datetime.now(timezone.utc)
        started_at = request_log.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        request_log.status = status
        request_log.response_body = response_body
        request_log.ended_at = ended_at
        request_log.duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        self.db.add(request_log)
        if status == "succeeded" and request_log.route_mode not in {"task_lookup", "task_lookup_cache"}:
            BusinessTrackingService(self.db).mark_first_activated(
                user_id=request_log.user_id,
                occurred_at=ended_at,
            )
        ModelMetricsRollupService(self.db).record_request_result(request_log, ended_at=ended_at)
        self.db.commit()
        self.db.refresh(request_log)
        return request_log
