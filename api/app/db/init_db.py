from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.base import Base
from app.db.session import async_engine, sync_engine
from app.domains.platform.entities import entities as _entities  # noqa: F401
from app.domains.platform.entities.entities import (
    PlatformModel,
    PlatformModelProviderBinding,
    PlatformModelRoute,
)
from app.domains.platform.services.platform_bootstrap_source import build_platform_bootstrap
from app.domains.platform.services.platform_config_snapshot import reload_platform_config_snapshot

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _ensure_sqlite_database_parent() -> None:
    database = make_url(settings.database_url).database or ""
    if not database or database == ":memory:":
        return
    db_path = Path(database)
    if not db_path.is_absolute():
        db_path = (_BACKEND_ROOT / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _seed_platform_bootstrap_if_needed() -> None:
    bootstrap = build_platform_bootstrap()
    bootstrap_model_codes = {row.public_model_code for row in bootstrap.models}
    with sync_engine.begin() as connection:
        if bootstrap_model_codes:
            connection.execute(
                delete(PlatformModelProviderBinding).where(
                    PlatformModelProviderBinding.model_code.in_(bootstrap_model_codes)
                )
            )
            connection.execute(
                delete(PlatformModelRoute).where(
                    PlatformModelRoute.model_code.in_(bootstrap_model_codes)
                )
            )
            connection.execute(
                delete(PlatformModel).where(
                    PlatformModel.model_code.in_(bootstrap_model_codes)
                )
            )

        model_rows = [
            {
                "model_code": row.public_model_code,
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
        ]
        if model_rows:
            connection.execute(PlatformModel.__table__.insert(), model_rows)

        route_rows = [
            {
                "model_code": row.public_model_code,
                "route_group": row.route_group,
                "is_primary": row.is_primary,
                "public_api_visible": row.public_api_visible,
                "endpoints_json": row.endpoints_json,
                "api_doc_json": row.api_doc_json,
                "supported_input_modes_json": row.supported_input_modes_json,
                "default_chain_json": row.default_chain_json,
            }
            for row in bootstrap.routes
        ]
        if route_rows:
            connection.execute(PlatformModelRoute.__table__.insert(), route_rows)

        binding_rows = [
            {
                "model_code": row.public_model_code,
                "route_group": row.route_group,
                "provider_code": row.provider_code,
                "enabled": row.enabled,
                "execution_model_code": row.execution_model_code,
                "pricing_strategy": row.pricing_strategy,
                "is_async": row.is_async,
                "is_streaming": row.is_streaming,
            }
            for row in bootstrap.provider_bindings
        ]
        if binding_rows:
            connection.execute(PlatformModelProviderBinding.__table__.insert(), binding_rows)


def init_app_db() -> None:
    if not settings.database_is_sqlite:
        raise RuntimeError("35gateway open-source backend only supports sqlite.")
    _ensure_sqlite_database_parent()
    Base.metadata.create_all(bind=sync_engine)
    _seed_platform_bootstrap_if_needed()
    reload_platform_config_snapshot()


async def close_app_db() -> None:
    await async_engine.dispose()
    sync_engine.dispose()


# 兼容旧入口
init_db = init_app_db
