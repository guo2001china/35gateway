from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import ProviderMetricsHourly


SUPPORTED_PROVIDER_METRICS_WINDOWS = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


class ProviderMetricsRollupService:
    def __init__(self, db: Session):
        self.db = db

    def parse_window(self, window: str | None) -> str:
        effective = (window or "24h").strip() or "24h"
        if effective not in SUPPORTED_PROVIDER_METRICS_WINDOWS:
            raise HTTPException(status_code=400, detail="unsupported_window")
        return effective

    def window_cutoff(self, window: str | None) -> datetime:
        effective = self.parse_window(window)
        return datetime.now(timezone.utc) - SUPPORTED_PROVIDER_METRICS_WINDOWS[effective]

    def record_result(
        self,
        *,
        provider_code: str,
        execution_model_code: str,
        status: str,
        duration_ms: int | None,
        error_message: str | None,
        ended_at: datetime,
    ) -> None:
        bucket_start = self._bucket_start(ended_at)
        row = (
            self.db.query(ProviderMetricsHourly)
            .filter(
                ProviderMetricsHourly.bucket_start == bucket_start,
                ProviderMetricsHourly.provider_code == provider_code,
                ProviderMetricsHourly.execution_model_code == execution_model_code,
            )
            .first()
        )
        if row is None:
            row = ProviderMetricsHourly(
                bucket_start=bucket_start,
                provider_code=provider_code,
                execution_model_code=execution_model_code,
                sample_count=0,
                success_count=0,
                failure_count=0,
                duration_sum_ms=0,
            )
        row.sample_count += 1
        if status == "succeeded":
            row.success_count += 1
            if duration_ms is not None:
                row.duration_sum_ms += int(duration_ms)
        else:
            row.failure_count += 1
            if error_message:
                row.last_error_message = error_message
                row.last_error_at = ended_at
        self.db.add(row)

    def list_rows(
        self,
        *,
        window: str | None,
        provider_code: str | None = None,
    ) -> list[ProviderMetricsHourly]:
        cutoff = self._bucket_start(self.window_cutoff(window))
        query = self.db.query(ProviderMetricsHourly).filter(ProviderMetricsHourly.bucket_start >= cutoff)
        if provider_code:
            query = query.filter(ProviderMetricsHourly.provider_code == provider_code)
        return query.all()

    def _bucket_start(self, value: datetime) -> datetime:
        normalized = value.astimezone(timezone.utc)
        return normalized.replace(minute=0, second=0, microsecond=0)
