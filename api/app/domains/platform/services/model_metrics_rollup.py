from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import ModelMetricsHourly, Request, Task

_REQUEST_TERMINAL_STATUSES = {"succeeded", "failed"}
_TASK_TERMINAL_STATUSES = {"completed", "failed", "cancelled", "canceled"}


class ModelMetricsRollupService:
    def __init__(self, db: Session):
        self.db = db

    def record_request_result(self, request_row: Request, *, ended_at: datetime) -> None:
        if request_row.model_metrics_recorded_at is not None:
            return
        if not request_row.record_model_metrics:
            return
        if not request_row.public_model_code:
            return
        if request_row.status not in _REQUEST_TERMINAL_STATUSES:
            return
        if request_row.route_mode in {"task_lookup", "task_lookup_cache"}:
            return
        if self.db.query(Task.id).filter(Task.request_id == request_row.id).first() is not None:
            return

        bucket = self._get_or_create_bucket(
            bucket_start=self._bucket_start(ended_at),
            public_model_code=request_row.public_model_code,
            route_group=request_row.route_group,
        )
        bucket.sample_count += 1
        bucket.request_sample_count += 1
        if request_row.status == "succeeded":
            bucket.success_count += 1
            bucket.request_success_count += 1
        request_row.model_metrics_recorded_at = ended_at
        self.db.add(bucket)
        self.db.add(request_row)

    def record_task_result(self, task: Task, *, route_group: str, finished_at: datetime | None = None) -> None:
        if task.model_metrics_recorded_at is not None:
            return
        if not task.public_model_code:
            return
        if task.status not in _TASK_TERMINAL_STATUSES:
            return

        effective_finished_at = finished_at or task.finished_at or datetime.now(timezone.utc)
        bucket = self._get_or_create_bucket(
            bucket_start=self._bucket_start(effective_finished_at),
            public_model_code=task.public_model_code,
            route_group=route_group,
        )
        bucket.sample_count += 1
        bucket.task_sample_count += 1
        if task.status == "completed":
            bucket.success_count += 1
            bucket.task_success_count += 1
        task.model_metrics_recorded_at = effective_finished_at
        self.db.add(bucket)
        self.db.add(task)

    def _get_or_create_bucket(
        self,
        *,
        bucket_start: datetime,
        public_model_code: str,
        route_group: str,
    ) -> ModelMetricsHourly:
        row = (
            self.db.query(ModelMetricsHourly)
            .filter(
                ModelMetricsHourly.bucket_start == bucket_start,
                ModelMetricsHourly.public_model_code == public_model_code,
                ModelMetricsHourly.route_group == route_group,
            )
            .first()
        )
        if row is not None:
            return row
        return ModelMetricsHourly(
            bucket_start=bucket_start,
            public_model_code=public_model_code,
            route_group=route_group,
            sample_count=0,
            success_count=0,
            request_sample_count=0,
            request_success_count=0,
            task_sample_count=0,
            task_success_count=0,
        )

    def _bucket_start(self, value: datetime) -> datetime:
        normalized = value.astimezone(timezone.utc)
        return normalized.replace(minute=0, second=0, microsecond=0)
