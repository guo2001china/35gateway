from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.domains.platform.services.platform_config_snapshot import (
    PlatformConfigSnapshot,
    PlatformModelProviderBindingSnapshot,
    PlatformModelRouteSnapshot,
    PlatformModelSnapshot,
)


def _make_snapshot() -> PlatformConfigSnapshot:
    gpt = PlatformModelSnapshot(
        public_model_code="gpt-5.4",
        display_name="GPT-5.4",
        category="text",
        summary="Primary text model",
        status="ready",
        docs_url="https://docs.example.com/gpt-5.4",
        billing_unit="token",
        currency="CNY",
        multiplier=Decimal("1.25000000"),
        official_price={},
        provider_cost={"input_per_1m_tokens": "8.0", "output_per_1m_tokens": "16.0"},
        notes="",
        source_url="https://example.com/pricing",
        last_verified_at=datetime(2026, 3, 30, tzinfo=timezone.utc),
    )
    deepseek = PlatformModelSnapshot(
        public_model_code="DeepSeek-V3.2",
        display_name="DeepSeek V3.2",
        category="text",
        summary="Fallback text model",
        status="ready",
        docs_url=None,
        billing_unit="token",
        currency="CNY",
        multiplier=Decimal("1.11111111"),
        official_price={},
        provider_cost={},
        notes="",
        source_url=None,
        last_verified_at=None,
    )
    private_model = PlatformModelSnapshot(
        public_model_code="internal-demo",
        display_name="Internal Demo",
        category="text",
        summary="Internal route only",
        status="ready",
        docs_url=None,
        billing_unit=None,
        currency="CNY",
        multiplier=Decimal("1.11111111"),
        official_price={},
        provider_cost={},
        notes="",
        source_url=None,
        last_verified_at=None,
    )

    gpt_openai = PlatformModelRouteSnapshot(
        public_model_code="gpt-5.4",
        route_group="openai",
        is_primary=True,
        public_api_visible=True,
        endpoints={"create": "POST /v1/chat/completions"},
        api_doc={"request_schema": "chat"},
        supported_input_modes=("chat",),
        default_chain=("yunwu_openai", "35m"),
    )
    gpt_responses = PlatformModelRouteSnapshot(
        public_model_code="gpt-5.4",
        route_group="responses",
        is_primary=False,
        public_api_visible=False,
        endpoints={"create": "POST /v1/responses"},
        api_doc={"request_schema": "responses"},
        supported_input_modes=("input",),
        default_chain=("openai_official",),
    )
    deepseek_openai = PlatformModelRouteSnapshot(
        public_model_code="DeepSeek-V3.2",
        route_group="openai",
        is_primary=True,
        public_api_visible=True,
        endpoints={"create": "POST /v1/chat/completions"},
        api_doc={"request_schema": "chat"},
        supported_input_modes=("chat",),
        default_chain=("openrouter", "deepseek_official"),
    )
    private_route = PlatformModelRouteSnapshot(
        public_model_code="internal-demo",
        route_group="openai",
        is_primary=True,
        public_api_visible=False,
        endpoints={"create": "POST /internal/demo"},
        api_doc={},
        supported_input_modes=("chat",),
        default_chain=("openai_official",),
    )

    return PlatformConfigSnapshot(
        models={
            gpt.public_model_code: gpt,
            deepseek.public_model_code: deepseek,
            private_model.public_model_code: private_model,
        },
        routes={
            (gpt_openai.public_model_code, gpt_openai.route_group): gpt_openai,
            (gpt_responses.public_model_code, gpt_responses.route_group): gpt_responses,
            (deepseek_openai.public_model_code, deepseek_openai.route_group): deepseek_openai,
            (private_route.public_model_code, private_route.route_group): private_route,
        },
        routes_by_model={
            "gpt-5.4": (gpt_openai, gpt_responses),
            "DeepSeek-V3.2": (deepseek_openai,),
            "internal-demo": (private_route,),
        },
        public_routes_by_model={
            "gpt-5.4": (gpt_openai,),
            "DeepSeek-V3.2": (deepseek_openai,),
        },
        bindings_by_route={
            ("gpt-5.4", "openai"): (
                PlatformModelProviderBindingSnapshot(
                    public_model_code="gpt-5.4",
                    route_group="openai",
                    provider_code="yunwu_openai",
                    enabled=True,
                    execution_model_code="gpt-5.4",
                    pricing_strategy="text_tokens",
                    is_async=False,
                    is_streaming=True,
                ),
                PlatformModelProviderBindingSnapshot(
                    public_model_code="gpt-5.4",
                    route_group="openai",
                    provider_code="35m",
                    enabled=False,
                    execution_model_code="gpt-5.4-mini",
                    pricing_strategy="text_tokens",
                    is_async=False,
                    is_streaming=True,
                ),
            )
        },
    )


def test_get_primary_route_prefers_public_primary_and_falls_back_to_private_route() -> None:
    snapshot = _make_snapshot()

    assert snapshot.get_primary_route("gpt-5.4").route_group == "openai"
    assert snapshot.get_primary_route("internal-demo").route_group == "openai"


def test_list_public_models_returns_sorted_public_subset_only() -> None:
    snapshot = _make_snapshot()

    assert [item.public_model_code for item in snapshot.list_public_models()] == ["DeepSeek-V3.2", "gpt-5.4"]


def test_get_pricing_for_model_returns_model_backed_pricing_snapshot() -> None:
    snapshot = _make_snapshot()

    assert snapshot.get_pricing_for_model("gpt-5.4").public_model_code == "gpt-5.4"
    assert snapshot.get_pricing_for_model("DeepSeek-V3.2").public_model_code == "DeepSeek-V3.2"
    assert snapshot.get_pricing_for_model("internal-demo") is None
    assert snapshot.get_pricing_for_model("missing-model") is None


def test_list_bindings_filters_disabled_bindings_by_default() -> None:
    snapshot = _make_snapshot()

    enabled = snapshot.list_bindings("gpt-5.4", "openai")
    all_bindings = snapshot.list_bindings("gpt-5.4", "openai", enabled_only=False)

    assert [item.provider_code for item in enabled] == ["yunwu_openai"]
    assert [item.provider_code for item in all_bindings] == ["yunwu_openai", "35m"]
    assert all_bindings[1].execution_model_code == "gpt-5.4-mini"


def test_margin_snapshot_aggregates_multi_key_pricing_and_handles_not_applicable() -> None:
    snapshot = _make_snapshot()
    gpt_margin = snapshot.get_pricing_for_model("gpt-5.4").margin_snapshot
    deepseek_margin = snapshot.get_pricing_for_model("DeepSeek-V3.2").margin_snapshot

    assert gpt_margin["status"] == "computed"
    assert gpt_margin["price_keys"] == ["input_per_1m_tokens", "output_per_1m_tokens"]
    assert gpt_margin["gross_margin_ratio"] == "0.2000"

    assert deepseek_margin == {
        "billing_unit": "token",
        "status": "not_applicable",
    }


def test_resolve_public_model_code_maps_execution_model_back_to_public_model() -> None:
    snapshot = _make_snapshot()

    seedream_model = PlatformModelSnapshot(
        public_model_code="doubao-seedream-4.5",
        display_name="Doubao Seedream 4.5",
        category="image",
        summary="Image model",
        status="ready",
        docs_url=None,
        billing_unit="image",
        currency="CNY",
        multiplier=Decimal("1.11111111"),
        official_price={},
        provider_cost={"per_image": "0.10"},
        notes="",
        source_url=None,
        last_verified_at=None,
    )
    seedream_route = PlatformModelRouteSnapshot(
        public_model_code="doubao-seedream-4.5",
        route_group="seedream",
        is_primary=True,
        public_api_visible=True,
        endpoints={"create": "POST /v1/doubao-seedream-4.5"},
        api_doc={},
        supported_input_modes=("text",),
        default_chain=("volcengine_seedream",),
    )
    seedream_binding = PlatformModelProviderBindingSnapshot(
        public_model_code="doubao-seedream-4.5",
        route_group="seedream",
        provider_code="volcengine_seedream",
        enabled=True,
        execution_model_code="doubao-seedream-4-5-251128",
        pricing_strategy="image_seedream",
        is_async=False,
        is_streaming=False,
    )
    snapshot.models[seedream_model.public_model_code] = seedream_model
    snapshot.routes[(seedream_route.public_model_code, seedream_route.route_group)] = seedream_route
    snapshot.routes_by_model[seedream_route.public_model_code] = (seedream_route,)
    snapshot.public_routes_by_model[seedream_route.public_model_code] = (seedream_route,)
    snapshot.bindings_by_route[(seedream_binding.public_model_code, seedream_binding.route_group)] = (seedream_binding,)

    assert snapshot.resolve_public_model_code(
        route_group="seedream",
        model_code="doubao-seedream-4-5-251128",
    ) == "doubao-seedream-4.5"
    assert snapshot.resolve_public_model_code(
        route_group="seedream",
        model_code="doubao-seedream-4.5",
    ) == "doubao-seedream-4.5"
