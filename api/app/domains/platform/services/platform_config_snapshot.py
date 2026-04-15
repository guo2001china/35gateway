from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from threading import RLock
from typing import Any

from sqlalchemy.orm import Session

from app.core.pricing.common import (
    DEFAULT_MODEL_MULTIPLIER,
    apply_multiplier_to_price_fields,
    derive_multiplier_from_price_fields,
    gross_margin_ratio,
)
from app.db.session import SessionLocal
from app.domains.platform.entities.entities import (
    PlatformModel,
    PlatformModelProviderBinding,
    PlatformModelRoute,
)


@dataclass(frozen=True)
class PlatformModelSnapshot:
    public_model_code: str
    display_name: str
    category: str
    summary: str
    status: str
    docs_url: str | None
    billing_unit: str | None
    currency: str
    multiplier: Decimal
    official_price: dict[str, Any]
    provider_cost: dict[str, Any]
    notes: str
    source_url: str | None
    last_verified_at: datetime | None

    @property
    def sale_price_fields(self) -> dict[str, Any]:
        return apply_multiplier_to_price_fields(self.provider_cost, multiplier=self.multiplier)

    @property
    def margin_snapshot(self) -> dict[str, Any]:
        if not self.billing_unit:
            return {"status": "not_applicable"}
        return _derive_margin_snapshot(
            billing_unit=self.billing_unit,
            sale_price=self.sale_price_fields,
            provider_cost=self.provider_cost,
        )


@dataclass(frozen=True)
class PlatformModelRouteSnapshot:
    public_model_code: str
    route_group: str
    is_primary: bool
    public_api_visible: bool
    endpoints: dict[str, Any]
    api_doc: dict[str, Any]
    supported_input_modes: tuple[str, ...]
    default_chain: tuple[str, ...]


@dataclass(frozen=True)
class PlatformModelProviderBindingSnapshot:
    public_model_code: str
    route_group: str
    provider_code: str
    enabled: bool
    execution_model_code: str
    pricing_strategy: str
    is_async: bool
    is_streaming: bool


@dataclass(frozen=True)
class PlatformConfigSnapshot:
    models: dict[str, PlatformModelSnapshot]
    routes: dict[tuple[str, str], PlatformModelRouteSnapshot]
    routes_by_model: dict[str, tuple[PlatformModelRouteSnapshot, ...]]
    public_routes_by_model: dict[str, tuple[PlatformModelRouteSnapshot, ...]]
    bindings_by_route: dict[tuple[str, str], tuple[PlatformModelProviderBindingSnapshot, ...]]

    def get_model(self, public_model_code: str) -> PlatformModelSnapshot:
        model = self.models.get(public_model_code)
        if model is None:
            raise KeyError(f"platform_model_not_found:{public_model_code}")
        return model

    def get_route(self, public_model_code: str, route_group: str) -> PlatformModelRouteSnapshot:
        route = self.routes.get((public_model_code, route_group))
        if route is None:
            raise KeyError(f"platform_model_route_not_found:{public_model_code}@{route_group}")
        return route

    def list_routes(
        self,
        public_model_code: str,
        *,
        public_only: bool = False,
    ) -> tuple[PlatformModelRouteSnapshot, ...]:
        mapping = self.public_routes_by_model if public_only else self.routes_by_model
        return mapping.get(public_model_code, ())

    def get_primary_route(
        self,
        public_model_code: str,
        *,
        public_only: bool = True,
    ) -> PlatformModelRouteSnapshot | None:
        routes = self.list_routes(public_model_code, public_only=public_only)
        if not routes and public_only:
            routes = self.list_routes(public_model_code, public_only=False)
        for route in routes:
            if route.is_primary:
                return route
        return routes[0] if routes else None

    def list_bindings(
        self,
        public_model_code: str,
        route_group: str,
        *,
        enabled_only: bool = True,
    ) -> tuple[PlatformModelProviderBindingSnapshot, ...]:
        bindings = self.bindings_by_route.get((public_model_code, route_group), ())
        if not enabled_only:
            return bindings
        return tuple(binding for binding in bindings if binding.enabled)

    def get_pricing_for_model(self, public_model_code: str) -> PlatformModelSnapshot | None:
        model = self.models.get(public_model_code)
        if model is None or not model.billing_unit:
            return None
        return model

    def list_public_models(self) -> tuple[PlatformModelSnapshot, ...]:
        public_model_codes = sorted(self.public_routes_by_model.keys())
        return tuple(
            self.models[public_model_code]
            for public_model_code in public_model_codes
            if public_model_code in self.models
        )

    def resolve_public_model_code(self, *, route_group: str, model_code: str | None) -> str | None:
        if not model_code:
            return model_code
        if (model_code, route_group) in self.routes:
            return model_code
        for (public_model_code, binding_route_group), bindings in self.bindings_by_route.items():
            if binding_route_group != route_group:
                continue
            for binding in bindings:
                if binding.execution_model_code == model_code:
                    return public_model_code
        return model_code


_SNAPSHOT_LOCK = RLock()
_PLATFORM_CONFIG_SNAPSHOT: PlatformConfigSnapshot | None = None


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _safe_tuple_str(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str) and item)


def _decimal_field_map(value: dict[str, Any]) -> dict[str, Decimal]:
    parsed: dict[str, Decimal] = {}
    for key, raw in value.items():
        try:
            parsed[key] = Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError):
            continue
    return parsed


def _derive_margin_snapshot(
    *,
    billing_unit: str,
    sale_price: dict[str, Any],
    provider_cost: dict[str, Any],
) -> dict[str, Any]:
    sale_fields = _decimal_field_map(sale_price)
    cost_fields = _decimal_field_map(provider_cost)
    shared_keys = [key for key in sale_fields if key in cost_fields]
    if not shared_keys:
        return {
            "billing_unit": billing_unit,
            "status": "not_applicable",
        }

    if len(shared_keys) > 1:
        per_key: dict[str, dict[str, str | None]] = {}
        ratios: list[Decimal] = []
        for key in shared_keys:
            sale_amount = sale_fields[key]
            cost_amount = cost_fields[key]
            ratio = gross_margin_ratio(sale_amount=sale_amount, cost_amount=cost_amount)
            if ratio is not None:
                ratios.append(ratio)
            per_key[key] = {
                "sale_unit_price": str(sale_amount),
                "cost_unit_price": str(cost_amount),
                "margin_per_unit": str(sale_amount - cost_amount),
                "gross_margin_ratio": None if ratio is None else str(ratio),
            }

        payload: dict[str, Any] = {
            "billing_unit": billing_unit,
            "status": "computed",
            "price_keys": shared_keys,
            "per_key": per_key,
            "notes": "多档价格，详见 per_key。",
        }
        if ratios:
            unique_ratios = {str(value) for value in ratios}
            if len(unique_ratios) == 1:
                payload["gross_margin_ratio"] = next(iter(unique_ratios))
            else:
                payload["gross_margin_ratio_min"] = str(min(ratios))
                payload["gross_margin_ratio_max"] = str(max(ratios))
        return payload

    key = shared_keys[0]
    sale_amount = sale_fields[key]
    cost_amount = cost_fields[key]
    ratio = gross_margin_ratio(sale_amount=sale_amount, cost_amount=cost_amount)
    return {
        "billing_unit": billing_unit,
        "status": "computed",
        "price_key": key,
        "sale_unit_price": str(sale_amount),
        "cost_unit_price": str(cost_amount),
        "margin_per_unit": str(sale_amount - cost_amount),
        "gross_margin_ratio": None if ratio is None else str(ratio),
    }


def _resolve_multiplier(*, row: PlatformModel) -> Decimal:
    if row.multiplier is not None:
        return Decimal(str(row.multiplier))
    derived = derive_multiplier_from_price_fields(cost_price_fields=_safe_dict(row.provider_cost_json))
    return derived or DEFAULT_MODEL_MULTIPLIER


def build_platform_config_snapshot(db: Session) -> PlatformConfigSnapshot:
    models = {
        row.model_code: PlatformModelSnapshot(
            public_model_code=row.model_code,
            display_name=row.display_name,
            category=row.category,
            summary=row.summary or "",
            status=row.status,
            docs_url=row.docs_url,
            billing_unit=row.billing_unit,
            currency=row.currency,
            multiplier=_resolve_multiplier(row=row),
            official_price=_safe_dict(row.official_price_json),
            provider_cost=_safe_dict(row.provider_cost_json),
            notes=row.notes or "",
            source_url=row.source_url,
            last_verified_at=row.last_verified_at,
        )
        for row in db.query(PlatformModel).all()
    }

    route_rows = db.query(PlatformModelRoute).all()
    routes: dict[tuple[str, str], PlatformModelRouteSnapshot] = {}
    routes_by_model: dict[str, list[PlatformModelRouteSnapshot]] = defaultdict(list)
    public_routes_by_model: dict[str, list[PlatformModelRouteSnapshot]] = defaultdict(list)
    for row in route_rows:
        route = PlatformModelRouteSnapshot(
            public_model_code=row.model_code,
            route_group=row.route_group,
            is_primary=bool(row.is_primary),
            public_api_visible=bool(row.public_api_visible),
            endpoints=_safe_dict(row.endpoints_json),
            api_doc=_safe_dict(row.api_doc_json),
            supported_input_modes=_safe_tuple_str(row.supported_input_modes_json),
            default_chain=_safe_tuple_str(row.default_chain_json),
        )
        routes[(row.model_code, row.route_group)] = route
        routes_by_model[row.model_code].append(route)
        if route.public_api_visible:
            public_routes_by_model[row.model_code].append(route)

    def _route_sort_key(item: PlatformModelRouteSnapshot) -> tuple[int, str]:
        return (0 if item.is_primary else 1, item.route_group)

    normalized_routes_by_model = {
        model_code: tuple(sorted(items, key=_route_sort_key))
        for model_code, items in routes_by_model.items()
    }
    normalized_public_routes_by_model = {
        model_code: tuple(sorted(items, key=_route_sort_key))
        for model_code, items in public_routes_by_model.items()
    }

    binding_rows = db.query(PlatformModelProviderBinding).all()
    bindings_by_route: dict[tuple[str, str], list[PlatformModelProviderBindingSnapshot]] = defaultdict(list)
    for row in binding_rows:
        bindings_by_route[(row.model_code, row.route_group)].append(
            PlatformModelProviderBindingSnapshot(
                public_model_code=row.model_code,
                route_group=row.route_group,
                provider_code=row.provider_code,
                enabled=bool(row.enabled),
                execution_model_code=row.execution_model_code,
                pricing_strategy=row.pricing_strategy,
                is_async=bool(row.is_async),
                is_streaming=bool(row.is_streaming),
            )
        )
    normalized_bindings_by_route = {
        key: tuple(sorted(items, key=lambda item: item.provider_code))
        for key, items in bindings_by_route.items()
    }

    return PlatformConfigSnapshot(
        models=models,
        routes=routes,
        routes_by_model=normalized_routes_by_model,
        public_routes_by_model=normalized_public_routes_by_model,
        bindings_by_route=normalized_bindings_by_route,
    )


def reload_platform_config_snapshot(db: Session | None = None) -> PlatformConfigSnapshot:
    global _PLATFORM_CONFIG_SNAPSHOT

    if db is not None:
        snapshot = build_platform_config_snapshot(db)
    else:
        with SessionLocal() as session:
            snapshot = build_platform_config_snapshot(session)

    with _SNAPSHOT_LOCK:
        _PLATFORM_CONFIG_SNAPSHOT = snapshot
    return snapshot


def get_platform_config_snapshot() -> PlatformConfigSnapshot:
    with _SNAPSHOT_LOCK:
        snapshot = _PLATFORM_CONFIG_SNAPSHOT
    if snapshot is None:
        snapshot = reload_platform_config_snapshot()
    return snapshot
