from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from decimal import Decimal
from typing import Any, Callable, TypeVar

from app.core.pricing.common import DEFAULT_MODEL_MULTIPLIER, derive_multiplier_from_price_fields

@dataclass(frozen=True)
class BootstrapModelRow:
    public_model_code: str
    display_name: str
    category: str
    summary: str
    status: str
    docs_url: str | None
    billing_unit: str | None
    currency: str
    multiplier: Decimal
    official_price_json: dict[str, Any]
    provider_cost_json: dict[str, Any]
    notes: str
    source_url: str | None
    last_verified_at: datetime | None


@dataclass(frozen=True)
class BootstrapRouteRow:
    public_model_code: str
    route_group: str
    endpoints_json: dict[str, Any]
    api_doc_json: dict[str, Any]
    supported_input_modes_json: list[str]
    is_primary: bool
    public_api_visible: bool
    default_chain_json: list[str]


@dataclass(frozen=True)
class BootstrapProviderBindingRow:
    public_model_code: str
    route_group: str
    provider_code: str
    execution_model_code: str
    pricing_strategy: str
    is_async: bool
    is_streaming: bool
    enabled: bool


@dataclass(frozen=True)
class PlatformBootstrap:
    models: tuple[BootstrapModelRow, ...]
    routes: tuple[BootstrapRouteRow, ...]
    provider_bindings: tuple[BootstrapProviderBindingRow, ...]


_BOOTSTRAP_DATA_PATH = Path(__file__).resolve().parent / "platform_bootstrap_data.json"
_RowT = TypeVar("_RowT")


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


@lru_cache(maxsize=1)
def _load_bootstrap_payload() -> dict[str, Any]:
    return json.loads(_BOOTSTRAP_DATA_PATH.read_text(encoding="utf-8"))


def _load_models(rows: list[dict[str, Any]]) -> tuple[BootstrapModelRow, ...]:
    return tuple(
        BootstrapModelRow(
            public_model_code=str(row["model_code"]),
            display_name=str(row["display_name"]),
            category=str(row["category"]),
            summary=str(row.get("summary") or ""),
            status=str(row["status"]),
            docs_url=row.get("docs_url"),
            billing_unit=None if row.get("billing_unit") in (None, "") else str(row["billing_unit"]),
            currency=str(row.get("currency") or "CNY"),
            multiplier=_parse_multiplier(row),
            official_price_json=dict(row.get("official_price_json") or {}),
            provider_cost_json=dict(row.get("provider_cost_json") or {}),
            notes=str(row.get("notes") or ""),
            source_url=row.get("source_url"),
            last_verified_at=_parse_datetime(row.get("last_verified_at")),
        )
        for row in rows
    )


def _load_routes(rows: list[dict[str, Any]]) -> tuple[BootstrapRouteRow, ...]:
    return tuple(
        BootstrapRouteRow(
            public_model_code=str(row["model_code"]),
            route_group=str(row["route_group"]),
            endpoints_json=dict(row.get("endpoints_json") or {}),
            api_doc_json=dict(row.get("api_doc_json") or {}),
            supported_input_modes_json=list(row.get("supported_input_modes_json") or []),
            is_primary=bool(row.get("is_primary", True)),
            public_api_visible=bool(row.get("public_api_visible", True)),
            default_chain_json=list(row.get("default_chain_json") or []),
        )
        for row in rows
    )


def _load_provider_bindings(rows: list[dict[str, Any]]) -> tuple[BootstrapProviderBindingRow, ...]:
    return tuple(
        BootstrapProviderBindingRow(
            public_model_code=str(row["model_code"]),
            route_group=str(row["route_group"]),
            provider_code=str(row["provider_code"]),
            execution_model_code=str(row["execution_model_code"]),
            pricing_strategy=str(row["pricing_strategy"]),
            is_async=bool(row.get("is_async", False)),
            is_streaming=bool(row.get("is_streaming", False)),
            enabled=bool(row.get("enabled", True)),
        )
        for row in rows
    )


def _parse_multiplier(row: dict[str, Any]) -> Decimal:
    raw_multiplier = row.get("multiplier")
    if raw_multiplier not in (None, ""):
        return Decimal(str(raw_multiplier))
    derived = derive_multiplier_from_price_fields(
        cost_price_fields=dict(row.get("provider_cost_json") or {}),
    )
    return derived or DEFAULT_MODEL_MULTIPLIER


def _ensure_unique(
    rows: tuple[_RowT, ...],
    *,
    key_fn: Callable[[_RowT], object],
    label: str,
) -> tuple[_RowT, ...]:
    seen: set[object] = set()
    for row in rows:
        key = key_fn(row)
        if key in seen:
            raise ValueError(f"duplicate {label}: {key!r}")
        seen.add(key)
    return rows


def _build_platform_bootstrap_from_payload(payload: dict[str, Any]) -> PlatformBootstrap:
    models = _ensure_unique(
        _load_models(list(payload.get("models") or [])),
        key_fn=lambda row: row.public_model_code,
        label="platform public_model_code",
    )
    routes = _ensure_unique(
        _load_routes(list(payload.get("routes") or [])),
        key_fn=lambda row: (row.public_model_code, row.route_group),
        label="platform model route",
    )
    provider_bindings = _ensure_unique(
        _load_provider_bindings(list(payload.get("provider_bindings") or [])),
        key_fn=lambda row: (row.public_model_code, row.route_group, row.provider_code),
        label="platform model provider binding",
    )

    public_model_codes = {row.public_model_code for row in models}
    route_keys = {(row.public_model_code, row.route_group) for row in routes}
    enabled_bindings_by_route: dict[tuple[str, str], set[str]] = {}
    for route in routes:
        if route.public_model_code not in public_model_codes:
            raise ValueError(f"route references unknown public_model_code: {route.public_model_code!r}")
    for binding in provider_bindings:
        route_key = (binding.public_model_code, binding.route_group)
        if route_key not in route_keys:
            raise ValueError(f"provider binding references unknown route: {route_key!r}")
        if binding.enabled:
            enabled_bindings_by_route.setdefault(route_key, set()).add(binding.provider_code)

    for route in routes:
        enabled_provider_codes = enabled_bindings_by_route.get((route.public_model_code, route.route_group), set())
        default_chain = [code for code in route.default_chain_json if code]
        if route.public_api_visible and enabled_provider_codes and not default_chain:
            raise ValueError(
                f"public route missing default_chain_json: {(route.public_model_code, route.route_group)!r}"
            )
        if not set(default_chain).issubset(enabled_provider_codes):
            raise ValueError(
                f"default_chain_json must be a subset of enabled bindings: {(route.public_model_code, route.route_group)!r}"
            )

    return PlatformBootstrap(
        models=models,
        routes=routes,
        provider_bindings=provider_bindings,
    )


def build_platform_bootstrap() -> PlatformBootstrap:
    return _build_platform_bootstrap_from_payload(_load_bootstrap_payload())
