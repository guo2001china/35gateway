from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_bootstrap_module():
    script_path = Path(__file__).resolve().parents[3] / "api" / "scripts" / "bootstrap_platform_config.py"
    spec = importlib.util.spec_from_file_location("bootstrap_platform_config_test_module", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeInsert:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self.payload = None
        self.index_elements = None
        self.set_ = None
        self.excluded = None

    def values(self, **row):
        self.payload = row
        self.excluded = SimpleNamespace(**row)
        return self

    def on_conflict_do_update(self, *, index_elements, set_):
        self.index_elements = list(index_elements)
        self.set_ = dict(set_)
        return self


class _FakeInsertFactory:
    def __init__(self):
        self.statements = []

    def __call__(self, model_cls):
        stmt = _FakeInsert(model_cls)
        self.statements.append(stmt)
        return stmt


class _FakeSession:
    def __init__(self):
        self.executed = []

    def execute(self, stmt):
        self.executed.append(stmt)


def test_bootstrap_models_updates_model_and_pricing_fields(monkeypatch) -> None:
    sync_module = _load_bootstrap_module()
    fake_insert = _FakeInsertFactory()
    session = _FakeSession()
    monkeypatch.setattr(sync_module, "insert", fake_insert)

    sync_module._sync_models(
        session,
        [
            {
                "model_code": "gpt-5.4",
                "display_name": "GPT-5.4",
                "category": "text",
                "summary": "summary",
                "status": "available",
                "docs_url": "https://example.com",
                "billing_unit": "token",
                "currency": "CNY",
                "multiplier": "2.00000000",
                "official_price_json": {"input_per_1m_tokens": "8.0"},
                "provider_cost_json": {"input_per_1m_tokens": "8.0"},
                "notes": "ops note",
                "source_url": "https://example.com/pricing",
                "last_verified_at": None,
            }
        ],
    )

    stmt = session.executed[0]
    assert stmt.index_elements == ["model_code"]
    assert set(stmt.set_.keys()) == {
        "display_name",
        "category",
        "summary",
        "status",
        "docs_url",
        "billing_unit",
        "currency",
        "multiplier",
        "official_price_json",
        "provider_cost_json",
        "notes",
        "source_url",
        "last_verified_at",
        "updated_at",
    }


def test_bootstrap_routes_preserves_route_fields(monkeypatch) -> None:
    sync_module = _load_bootstrap_module()
    fake_insert = _FakeInsertFactory()
    session = _FakeSession()
    monkeypatch.setattr(sync_module, "insert", fake_insert)

    sync_module._sync_routes(
        session,
        [
            {
                "model_code": "gpt-5.4",
                "route_group": "openai",
                "is_primary": True,
                "public_api_visible": False,
                "endpoints_json": {"create": "POST /v1/chat/completions"},
                "api_doc_json": {"request_schema": "chat"},
                "supported_input_modes_json": ["chat"],
                "default_chain_json": ["35m"],
            }
        ],
    )

    stmt = session.executed[0]
    assert stmt.index_elements == ["model_code", "route_group"]
    assert set(stmt.set_.keys()) == {
        "is_primary",
        "public_api_visible",
        "endpoints_json",
        "api_doc_json",
        "supported_input_modes_json",
        "default_chain_json",
        "updated_at",
    }


def test_bootstrap_provider_bindings_updates_technical_binding_fields(monkeypatch) -> None:
    sync_module = _load_bootstrap_module()
    fake_insert = _FakeInsertFactory()
    session = _FakeSession()
    monkeypatch.setattr(sync_module, "insert", fake_insert)

    sync_module._sync_provider_bindings(
        session,
        [
            {
                "model_code": "DeepSeek-V3.2",
                "route_group": "openai",
                "provider_code": "openrouter",
                "enabled": True,
                "execution_model_code": "deepseek/deepseek-chat-v3.1",
                "pricing_strategy": "text_tokens",
                "is_async": False,
                "is_streaming": True,
            }
        ],
    )

    stmt = session.executed[0]
    assert stmt.index_elements == ["model_code", "route_group", "provider_code"]
    assert set(stmt.set_.keys()) == {
        "enabled",
        "execution_model_code",
        "pricing_strategy",
        "is_async",
        "is_streaming",
        "updated_at",
    }
