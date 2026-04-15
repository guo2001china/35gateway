from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import ModelMetricsHourly
from app.domains.platform.services.provider_metrics import MIN_SAMPLE_COUNT, SUPPORTED_WINDOWS


class ModelMetricsService:
    def __init__(self, db: Session):
        self.db = db

    def parse_window(self, window: str | None) -> str:
        effective = window or "24h"
        if effective not in SUPPORTED_WINDOWS:
            raise HTTPException(status_code=400, detail="unsupported_window")
        return effective

    def default_metrics(self, window: str | None = None) -> dict[str, Any]:
        effective_window = self.parse_window(window)
        return {
            "window": effective_window,
            "sample_count": 0,
            "success_count": 0,
            "success_rate": None,
            "sample_ready": False,
        }

    def metrics_for_route_map(
        self,
        route_map: dict[str, str],
        window: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        effective_window = self.parse_window(window)
        normalized_model_codes = sorted({code for code in route_map.keys() if code})
        if not normalized_model_codes:
            return {}

        cutoff = self._bucket_start(datetime.now(timezone.utc) - SUPPORTED_WINDOWS[effective_window])
        rows = (
            self.db.query(ModelMetricsHourly)
            .filter(ModelMetricsHourly.public_model_code.in_(normalized_model_codes))
            .filter(ModelMetricsHourly.route_group.in_(sorted(set(route_map.values()))))
            .filter(ModelMetricsHourly.bucket_start >= cutoff)
            .all()
        )

        metrics: dict[str, dict[str, Any]] = {}
        for row in rows:
            if route_map.get(row.public_model_code) != row.route_group:
                continue
            bucket = metrics.setdefault(
                row.public_model_code,
                {
                    "window": effective_window,
                    "sample_count": 0,
                    "success_count": 0,
                },
            )
            bucket["sample_count"] += row.sample_count
            bucket["success_count"] += row.success_count

        for model_code, bucket in metrics.items():
            sample_count = bucket["sample_count"]
            success_count = bucket["success_count"]
            bucket["success_rate"] = round((success_count / sample_count) * 100, 2) if sample_count else None
            bucket["sample_ready"] = sample_count >= MIN_SAMPLE_COUNT
            metrics[model_code] = bucket

        return metrics

    def _bucket_start(self, value: datetime) -> datetime:
        normalized = value.astimezone(timezone.utc)
        return normalized.replace(minute=0, second=0, microsecond=0)
