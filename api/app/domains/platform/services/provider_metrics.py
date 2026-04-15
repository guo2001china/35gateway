from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from math import ceil
from statistics import median
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import ProviderRequest


SUPPORTED_WINDOWS = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}

MIN_SAMPLE_COUNT = 20


class ProviderMetricsService:
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
            "latency": {"avg_ms": None, "p50_ms": None, "p95_ms": None, "sample_count": 0},
        }

    def provider_metrics(self, execution_model_code: str, window: str | None) -> dict[str, dict[str, Any]]:
        return self.provider_metrics_for_model_codes([execution_model_code], window)

    def provider_metrics_for_model_codes(
        self,
        execution_model_codes: Iterable[str],
        window: str | None,
    ) -> dict[str, dict[str, Any]]:
        effective_window = self.parse_window(window)
        normalized_execution_model_codes = sorted({code for code in execution_model_codes if code})
        if not normalized_execution_model_codes:
            return {}

        cutoff = datetime.now(timezone.utc) - SUPPORTED_WINDOWS[effective_window]
        rows = (
            self.db.query(ProviderRequest)
            .filter(ProviderRequest.execution_model_code.in_(normalized_execution_model_codes))
            .filter(ProviderRequest.started_at >= cutoff)
            .all()
        )

        metrics: dict[str, dict[str, Any]] = {}
        for row in rows:
            bucket = metrics.setdefault(
                row.provider_code,
                {"window": effective_window, "sample_count": 0, "success_count": 0, "latencies": []},
            )
            bucket["sample_count"] += 1
            if row.status == "succeeded":
                bucket["success_count"] += 1
                if row.duration_ms is not None:
                    bucket["latencies"].append(row.duration_ms)

        for bucket in metrics.values():
            sample_count = bucket["sample_count"]
            success_count = bucket["success_count"]
            latencies = bucket.pop("latencies")
            success_rate = round((success_count / sample_count) * 100, 2) if sample_count else None
            bucket["success_rate"] = success_rate
            bucket["sample_ready"] = sample_count >= MIN_SAMPLE_COUNT
            bucket["latency"] = {
                "avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "p50_ms": median(latencies) if latencies else None,
                "p95_ms": self._percentile(latencies, 0.95),
                "sample_count": len(latencies),
            }
        return metrics

    def _percentile(self, values: list[int], percentile: float) -> int | None:
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, ceil(percentile * len(ordered)) - 1)
        return ordered[index]
