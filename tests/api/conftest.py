from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import pytest


TESTS_ROOT = Path(__file__).resolve().parent
API_ROOT = TESTS_ROOT.parent
ACTIVE_DB_PATH = TESTS_ROOT / ".console-test.sqlite3"
TEMPLATE_DB_PATH = TESTS_ROOT / ".console-test.template.sqlite3"

os.environ["APP_ENV"] = "test"
os.environ["API35_APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{ACTIVE_DB_PATH}"
os.environ["API35_DATABASE_URL"] = os.environ["DATABASE_URL"]

from app.db.base import Base
from app.db.session import AsyncSessionLocal, SessionLocal, async_engine, sync_engine
from app.domains.platform.entities import entities as _entities  # noqa: F401
from app.domains.platform.entities.entities import (
    PlatformModel,
    PlatformModelProviderBinding,
    PlatformModelRoute,
)
from app.domains.platform.services import auth_sessions
from app.domains.platform.services.platform_bootstrap_source import build_platform_bootstrap
from app.domains.platform.services.platform_config_snapshot import reload_platform_config_snapshot


class _FakeAuthStore:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> bool:
        self._store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def expire(self, key: str, _ttl: int) -> bool:
        return key in self._store

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                removed += 1
        return removed

    def flushall(self) -> None:
        self._store.clear()


_FAKE_AUTH_STORE = _FakeAuthStore()
auth_sessions.get_auth_store = lambda: _FAKE_AUTH_STORE


def _dispose_engines() -> None:
    sync_engine.dispose()
    asyncio.run(async_engine.dispose())


def _seed_platform_bootstrap() -> None:
    bootstrap = build_platform_bootstrap()
    with SessionLocal() as session:
        session.add_all(
            [
                PlatformModel(
                    model_code=row.public_model_code,
                    display_name=row.display_name,
                    category=row.category,
                    summary=row.summary,
                    status=row.status,
                    docs_url=row.docs_url,
                    billing_unit=row.billing_unit,
                    currency=row.currency,
                    multiplier=row.multiplier,
                    official_price_json=row.official_price_json,
                    provider_cost_json=row.provider_cost_json,
                    notes=row.notes,
                    source_url=row.source_url,
                    last_verified_at=row.last_verified_at,
                )
                for row in bootstrap.models
            ]
        )
        session.add_all(
            [
                PlatformModelRoute(
                    model_code=row.public_model_code,
                    route_group=row.route_group,
                    is_primary=row.is_primary,
                    public_api_visible=row.public_api_visible,
                    endpoints_json=row.endpoints_json,
                    api_doc_json=row.api_doc_json,
                    supported_input_modes_json=row.supported_input_modes_json,
                    default_chain_json=row.default_chain_json,
                )
                for row in bootstrap.routes
            ]
        )
        session.add_all(
            [
                PlatformModelProviderBinding(
                    model_code=row.public_model_code,
                    route_group=row.route_group,
                    provider_code=row.provider_code,
                    enabled=row.enabled,
                    execution_model_code=row.execution_model_code,
                    pricing_strategy=row.pricing_strategy,
                    is_async=row.is_async,
                    is_streaming=row.is_streaming,
                )
                for row in bootstrap.provider_bindings
            ]
        )
        session.commit()
        reload_platform_config_snapshot(session)


def _build_template_db() -> None:
    _dispose_engines()
    if ACTIVE_DB_PATH.exists():
        ACTIVE_DB_PATH.unlink()
    if TEMPLATE_DB_PATH.exists():
        TEMPLATE_DB_PATH.unlink()
    Base.metadata.create_all(bind=sync_engine)
    _seed_platform_bootstrap()
    _dispose_engines()
    shutil.copy2(ACTIVE_DB_PATH, TEMPLATE_DB_PATH)


def _restore_template_db() -> None:
    _dispose_engines()
    if ACTIVE_DB_PATH.exists():
        ACTIVE_DB_PATH.unlink()
    shutil.copy2(TEMPLATE_DB_PATH, ACTIVE_DB_PATH)
    _FAKE_AUTH_STORE.flushall()
    with SessionLocal() as session:
        reload_platform_config_snapshot(session)


@pytest.fixture(scope="session", autouse=True)
def _console_test_database_template() -> None:
    TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    _build_template_db()
    yield
    _dispose_engines()


@pytest.fixture(autouse=True)
def _reset_console_test_state() -> None:
    _restore_template_db()
    yield
    _dispose_engines()
    _FAKE_AUTH_STORE.flushall()
