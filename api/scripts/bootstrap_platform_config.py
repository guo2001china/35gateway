from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import delete, func, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.session import SessionLocal
from app.db.init_db import init_app_db
from app.domains.platform.entities.entities import (
    PlatformModel,
    PlatformModelProviderBinding,
    PlatformModelRoute,
)
from app.domains.platform.services.platform_bootstrap_source import build_platform_bootstrap
from app.domains.platform.services.platform_config_snapshot import reload_platform_config_snapshot

insert = sqlite_insert


def _sync_models(session, rows: Iterable[dict]) -> int:
    count = 0
    for row in rows:
        stmt = insert(PlatformModel).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["model_code"],
            set_={
                "display_name": stmt.excluded.display_name,
                "category": stmt.excluded.category,
                "summary": stmt.excluded.summary,
                "status": stmt.excluded.status,
                "docs_url": stmt.excluded.docs_url,
                "billing_unit": stmt.excluded.billing_unit,
                "currency": stmt.excluded.currency,
                "multiplier": stmt.excluded.multiplier,
                "official_price_json": stmt.excluded.official_price_json,
                "provider_cost_json": stmt.excluded.provider_cost_json,
                "notes": stmt.excluded.notes,
                "source_url": stmt.excluded.source_url,
                "last_verified_at": stmt.excluded.last_verified_at,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        count += 1
    return count


def _sync_routes(session, rows: Iterable[dict]) -> int:
    count = 0
    for row in rows:
        stmt = insert(PlatformModelRoute).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["model_code", "route_group"],
            set_={
                "is_primary": stmt.excluded.is_primary,
                "public_api_visible": stmt.excluded.public_api_visible,
                "endpoints_json": stmt.excluded.endpoints_json,
                "api_doc_json": stmt.excluded.api_doc_json,
                "supported_input_modes_json": stmt.excluded.supported_input_modes_json,
                "default_chain_json": stmt.excluded.default_chain_json,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        count += 1
    return count


def _sync_provider_bindings(session, rows: Iterable[dict]) -> int:
    count = 0
    for row in rows:
        stmt = insert(PlatformModelProviderBinding).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["model_code", "route_group", "provider_code"],
            set_={
                "enabled": stmt.excluded.enabled,
                "execution_model_code": stmt.excluded.execution_model_code,
                "pricing_strategy": stmt.excluded.pricing_strategy,
                "is_async": stmt.excluded.is_async,
                "is_streaming": stmt.excluded.is_streaming,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        count += 1
    return count


def _prune_missing_rows(session, bootstrap) -> dict[str, int]:
    bootstrap_model_codes = {row.model_code for row in bootstrap.models}
    bootstrap_route_keys = {(row.model_code, row.route_group) for row in bootstrap.routes}
    bootstrap_binding_keys = {
        (row.model_code, row.route_group, row.provider_code) for row in bootstrap.provider_bindings
    }

    removed_provider_bindings = 0
    if bootstrap_binding_keys:
        removed_provider_bindings = session.execute(
            delete(PlatformModelProviderBinding).where(
                tuple_(
                    PlatformModelProviderBinding.model_code,
                    PlatformModelProviderBinding.route_group,
                    PlatformModelProviderBinding.provider_code,
                ).not_in(bootstrap_binding_keys)
            )
        ).rowcount or 0

    removed_routes = 0
    if bootstrap_route_keys:
        removed_routes = session.execute(
            delete(PlatformModelRoute).where(
                tuple_(
                    PlatformModelRoute.model_code,
                    PlatformModelRoute.route_group,
                ).not_in(bootstrap_route_keys)
            )
        ).rowcount or 0

    removed_models = 0
    if bootstrap_model_codes:
        removed_models = session.execute(
            delete(PlatformModel).where(PlatformModel.model_code.not_in(bootstrap_model_codes))
        ).rowcount or 0

    return {
        "provider_bindings": removed_provider_bindings,
        "routes": removed_routes,
        "models": removed_models,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize or rebuild platform configuration rows from the checked-in "
            "bootstrap artifact. This is not the normal runtime config workflow."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write bootstrap rows into the database. Without this flag, only print the planned counts.",
    )
    parser.add_argument(
        "--prune-missing",
        action="store_true",
        help="Delete database rows that are no longer present in the bootstrap payload.",
    )
    args = parser.parse_args()

    bootstrap = build_platform_bootstrap()
    print(
        f"bootstrap rows: models={len(bootstrap.models)} "
        f"routes={len(bootstrap.routes)} "
        f"provider_bindings={len(bootstrap.provider_bindings)}"
    )
    if not args.apply:
        print("dry-run only; pass --apply to initialize or rebuild database rows from bootstrap data.")
        return 0

    init_app_db()
    with SessionLocal() as session:
        models = _sync_models(
            session,
            (
                {
                    "model_code": row.model_code,
                    "display_name": row.display_name,
                    "category": row.category,
                    "summary": row.summary,
                    "status": row.status,
                    "docs_url": row.docs_url,
                    "billing_unit": row.billing_unit,
                    "currency": row.currency,
                    "multiplier": row.multiplier,
                    "official_price_json": row.official_price_json,
                    "provider_cost_json": row.provider_cost_json,
                    "notes": row.notes,
                    "source_url": row.source_url,
                    "last_verified_at": row.last_verified_at,
                }
                for row in bootstrap.models
            ),
        )
        routes = _sync_routes(
            session,
            (
                {
                    "model_code": row.model_code,
                    "route_group": row.route_group,
                    "is_primary": row.is_primary,
                    "public_api_visible": row.public_api_visible,
                    "endpoints_json": row.endpoints_json,
                    "api_doc_json": row.api_doc_json,
                    "supported_input_modes_json": row.supported_input_modes_json,
                    "default_chain_json": row.default_chain_json,
                }
                for row in bootstrap.routes
            ),
        )
        provider_bindings = _sync_provider_bindings(
            session,
            (
                {
                    "model_code": row.model_code,
                    "route_group": row.route_group,
                    "provider_code": row.provider_code,
                    "enabled": row.enabled,
                    "execution_model_code": row.execution_model_code,
                    "pricing_strategy": row.pricing_strategy,
                    "is_async": row.is_async,
                    "is_streaming": row.is_streaming,
                }
                for row in bootstrap.provider_bindings
            ),
        )
        removed = {"models": 0, "routes": 0, "provider_bindings": 0}
        if args.prune_missing:
            removed = _prune_missing_rows(session, bootstrap)
        session.commit()
        reload_platform_config_snapshot(session)

    print(
        f"applied rows: models={models} routes={routes} "
        f"provider_bindings={provider_bindings}"
    )
    if args.prune_missing:
        print(
            f"pruned rows: models={removed['models']} routes={removed['routes']} "
            f"provider_bindings={removed['provider_bindings']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
