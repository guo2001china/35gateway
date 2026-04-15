from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import init_db as init_db_module
from app.db.base import Base
from app.domains.platform.entities.entities import (
    PlatformModel,
    PlatformModelProviderBinding,
    PlatformModelRoute,
)
from app.domains.platform.services.platform_bootstrap_source import (
    BootstrapModelRow,
    BootstrapProviderBindingRow,
    BootstrapRouteRow,
    PlatformBootstrap,
)


def test_seed_platform_bootstrap_replaces_stale_sqlite_rows(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        connection.execute(
            PlatformModel.__table__.insert(),
            [
                {
                    "model_code": "gpt-5.4",
                    "display_name": "GPT-5.4",
                    "category": "text",
                    "summary": "stale",
                    "status": "available",
                    "billing_unit": "token",
                    "currency": "CNY",
                    "multiplier": Decimal("2"),
                    "official_price_json": {},
                    "provider_cost_json": {"input_per_1m_tokens": "1"},
                    "notes": "",
                }
            ],
        )
        connection.execute(
            PlatformModelRoute.__table__.insert(),
            [
                {
                    "model_code": "gpt-5.4",
                    "route_group": "openai",
                    "is_primary": True,
                    "public_api_visible": True,
                    "endpoints_json": {"create": "POST /v1/chat/completions"},
                    "api_doc_json": {},
                    "supported_input_modes_json": ["chat"],
                    "default_chain_json": ["openai_official", "openrouter"],
                }
            ],
        )
        connection.execute(
            PlatformModelProviderBinding.__table__.insert(),
            [
                {
                    "model_code": "gpt-5.4",
                    "route_group": "openai",
                    "provider_code": "openai_official",
                    "enabled": True,
                    "execution_model_code": "gpt-5.4",
                    "pricing_strategy": "text_tokens",
                    "is_async": False,
                    "is_streaming": True,
                },
                {
                    "model_code": "gpt-5.4",
                    "route_group": "openai",
                    "provider_code": "openrouter",
                    "enabled": True,
                    "execution_model_code": "openai/gpt-5.4",
                    "pricing_strategy": "text_tokens",
                    "is_async": False,
                    "is_streaming": True,
                },
            ],
        )

    monkeypatch.setattr(init_db_module, "sync_engine", engine)
    monkeypatch.setattr(
        init_db_module,
        "build_platform_bootstrap",
        lambda: PlatformBootstrap(
            models=(
                BootstrapModelRow(
                    public_model_code="gpt-5.4",
                    display_name="GPT-5.4",
                    category="text",
                    summary="fresh",
                    status="available",
                    docs_url=None,
                    billing_unit="token",
                    currency="CNY",
                    multiplier=Decimal("2"),
                    official_price_json={},
                    provider_cost_json={"input_per_1m_tokens": "1"},
                    notes="",
                    source_url=None,
                    last_verified_at=None,
                ),
                BootstrapModelRow(
                    public_model_code="seedance-2.0-fast",
                    display_name="Seedance 2.0 Fast",
                    category="video",
                    summary="new",
                    status="available",
                    docs_url=None,
                    billing_unit="second",
                    currency="CNY",
                    multiplier=Decimal("1.1111"),
                    official_price_json={},
                    provider_cost_json={"per_second": "1.6933"},
                    notes="",
                    source_url=None,
                    last_verified_at=None,
                ),
            ),
            routes=(
                BootstrapRouteRow(
                    public_model_code="gpt-5.4",
                    route_group="openai",
                    endpoints_json={"create": "POST /v1/chat/completions"},
                    api_doc_json={},
                    supported_input_modes_json=["chat"],
                    is_primary=True,
                    public_api_visible=True,
                    default_chain_json=["35m"],
                ),
                BootstrapRouteRow(
                    public_model_code="seedance-2.0-fast",
                    route_group="seedance",
                    endpoints_json={"create": "POST /v1/seedance-2.0-fast"},
                    api_doc_json={},
                    supported_input_modes_json=["text", "image"],
                    is_primary=True,
                    public_api_visible=True,
                    default_chain_json=["35m"],
                ),
            ),
            provider_bindings=(
                BootstrapProviderBindingRow(
                    public_model_code="gpt-5.4",
                    route_group="openai",
                    provider_code="35m",
                    execution_model_code="gpt-5.4",
                    pricing_strategy="text_tokens",
                    is_async=False,
                    is_streaming=True,
                    enabled=True,
                ),
                BootstrapProviderBindingRow(
                    public_model_code="seedance-2.0-fast",
                    route_group="seedance",
                    provider_code="35m",
                    execution_model_code="seedance-2.0-fast",
                    pricing_strategy="video_seedance",
                    is_async=True,
                    is_streaming=False,
                    enabled=True,
                ),
            ),
        ),
    )

    init_db_module._seed_platform_bootstrap_if_needed()

    with Session(engine) as session:
        route = session.execute(
            select(PlatformModelRoute).where(
                PlatformModelRoute.model_code == "gpt-5.4",
                PlatformModelRoute.route_group == "openai",
            )
        ).scalar_one()
        bindings = session.execute(
            select(PlatformModelProviderBinding).order_by(
                PlatformModelProviderBinding.model_code,
                PlatformModelProviderBinding.route_group,
                PlatformModelProviderBinding.provider_code,
            )
        ).scalars().all()

    assert route.default_chain_json == ["35m"]
    assert [(row.model_code, row.route_group, row.provider_code) for row in bindings] == [
        ("gpt-5.4", "openai", "35m"),
        ("seedance-2.0-fast", "seedance", "35m"),
    ]
