from __future__ import annotations

from decimal import Decimal

from app.domains.platform.services.platform_config_snapshot import (
    PlatformConfigSnapshot,
    PlatformModelProviderBindingSnapshot,
    PlatformModelRouteSnapshot,
    PlatformModelSnapshot,
)
from app.domains.platform.services.routing import NoAvailableProviderError, ProviderNotFoundError, RoutingService


def _model(model_code: str, *, category: str = "text", billing_unit: str | None = "token") -> PlatformModelSnapshot:
    return PlatformModelSnapshot(
        public_model_code=model_code,
        display_name=model_code,
        category=category,
        summary=f"{model_code} summary",
        status="available",
        docs_url=f"https://example.com/{model_code}",
        billing_unit=billing_unit,
        currency="CNY",
        multiplier=Decimal("1.11111111"),
        official_price={},
        provider_cost={"base": "1.0"} if billing_unit else {},
        notes="",
        source_url=None,
        last_verified_at=None,
    )


def _snapshot_for_route(
    *,
    model_code: str,
    route_group: str,
    default_chain: tuple[str, ...],
    bindings: tuple[PlatformModelProviderBindingSnapshot, ...],
    category: str = "text",
    billing_unit: str | None = "token",
) -> PlatformConfigSnapshot:
    model = _model(model_code, category=category, billing_unit=billing_unit)
    route = PlatformModelRouteSnapshot(
        public_model_code=model_code,
        route_group=route_group,
        is_primary=True,
        public_api_visible=True,
        endpoints={"create": f"POST /v1/{model_code}"},
        api_doc={},
        supported_input_modes=("chat",) if category == "text" else ("text",),
        default_chain=default_chain,
    )
    return PlatformConfigSnapshot(
        models={model.public_model_code: model},
        routes={(route.public_model_code, route.route_group): route},
        routes_by_model={model.public_model_code: (route,)},
        public_routes_by_model={model.public_model_code: (route,)},
        bindings_by_route={(route.public_model_code, route.route_group): bindings},
    )


def _gpt54_snapshot() -> PlatformConfigSnapshot:
    return _snapshot_for_route(
        model_code="gpt-5.4",
        route_group="openai",
        default_chain=("yunwu_openai", "openai_official", "ksyun_openai"),
        bindings=(
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
                provider_code="openai_official",
                enabled=True,
                execution_model_code="gpt-5.4",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code="gpt-5.4",
                route_group="openai",
                provider_code="ksyun_openai",
                enabled=True,
                execution_model_code="mog-3-global",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
        ),
    )


def _veo3_snapshot() -> PlatformConfigSnapshot:
    return _snapshot_for_route(
        model_code="veo-3-fast",
        route_group="veo3",
        default_chain=("fal_veo3", "google_veo3"),
        bindings=(
            PlatformModelProviderBindingSnapshot(
                public_model_code="veo-3-fast",
                route_group="veo3",
                provider_code="fal_veo3",
                enabled=True,
                execution_model_code="veo-3-fast",
                pricing_strategy="video_veo",
                is_async=False,
                is_streaming=False,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code="veo-3-fast",
                route_group="veo3",
                provider_code="google_veo3",
                enabled=True,
                execution_model_code="veo-3.0-fast-generate-001",
                pricing_strategy="video_veo",
                is_async=True,
                is_streaming=False,
            ),
        ),
        category="video",
        billing_unit="second",
    )


def _empty_default_chain_snapshot() -> PlatformConfigSnapshot:
    return _snapshot_for_route(
        model_code="glm-4.7-flash",
        route_group="openai",
        default_chain=(),
        bindings=(
            PlatformModelProviderBindingSnapshot(
                public_model_code="glm-4.7-flash",
                route_group="openai",
                provider_code="cloudflare_workers_ai",
                enabled=True,
                execution_model_code="@cf/zai-org/glm-4.7-flash",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
        ),
    )


def test_chain_stays_inside_requested_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    plan = service.plan(
        route_group="openai",
        requested_model="gpt-5.4",
        chain="yunwu_openai,openai_official",
        allow_fallback=True,
    )

    assert plan.route_mode == "chain"
    assert plan.route_plan == ["yunwu_openai", "openai_official"]


def test_chain_keeps_supported_subset_without_outside_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    plan = service.plan(
        route_group="openai",
        requested_model="gpt-5.4",
        chain="missing_provider,openai_official",
        allow_fallback=True,
    )

    assert plan.route_plan == ["openai_official"]


def test_chain_raises_when_no_requested_provider_is_supported(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    try:
        service.plan(
            route_group="openai",
            requested_model="gpt-5.4",
            chain="missing_provider",
            allow_fallback=True,
        )
    except ProviderNotFoundError as exc:
        assert str(exc) == "chain_not_found_or_not_supported"
    else:
        raise AssertionError("expected ProviderNotFoundError")


def test_default_route_without_fallback_only_tries_first_configured_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    plan = service.plan(
        route_group="openai",
        requested_model="gpt-5.4",
        chain=None,
        allow_fallback=False,
    )

    assert plan.route_mode == "default"
    assert plan.route_plan == ["yunwu_openai"]


def test_default_route_with_fallback_uses_full_configured_chain(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    plan = service.plan(
        route_group="openai",
        requested_model="gpt-5.4",
        chain=None,
        allow_fallback=True,
    )

    assert plan.route_mode == "default"
    assert plan.route_plan == ["yunwu_openai", "openai_official", "ksyun_openai"]


def test_default_route_requires_configured_default_chain(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _empty_default_chain_snapshot,
    )
    service = RoutingService()

    try:
        service.plan(
            route_group="openai",
            requested_model="glm-4.7-flash",
            chain=None,
            allow_fallback=True,
        )
    except NoAvailableProviderError as exc:
        assert str(exc) == "default_chain_not_configured"
    else:
        raise AssertionError("expected default_chain_not_configured")


def test_default_chain_returns_configured_order(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _gpt54_snapshot,
    )
    service = RoutingService()

    chain = service.default_chain(
        route_group="openai",
        requested_model="gpt-5.4",
        allow_fallback=True,
    )

    assert chain == "yunwu_openai,openai_official,ksyun_openai"


def test_default_chain_respects_allow_fallback_false(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        _veo3_snapshot,
    )
    service = RoutingService()

    chain = service.default_chain(
        route_group="veo3",
        requested_model="veo-3-fast",
        allow_fallback=False,
    )

    assert chain == "fal_veo3"


def test_unknown_provider_binding_is_skipped_in_runtime_routing(monkeypatch) -> None:
    snapshot = _snapshot_for_route(
        model_code="nano-banana-2",
        route_group="images",
        default_chain=("fal_nano_banana", "openrouter"),
        bindings=(
            PlatformModelProviderBindingSnapshot(
                public_model_code="nano-banana-2",
                route_group="images",
                provider_code="fal_nano_banana",
                enabled=True,
                execution_model_code="nano-banana-2",
                pricing_strategy="image_fixed_resolution",
                is_async=False,
                is_streaming=False,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code="nano-banana-2",
                route_group="images",
                provider_code="openrouter",
                enabled=True,
                execution_model_code="google/gemini-2.5-flash-image-preview",
                pricing_strategy="image_fixed_resolution",
                is_async=False,
                is_streaming=False,
            ),
        ),
        category="image",
        billing_unit="image",
    )
    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_platform_config_snapshot",
        lambda: snapshot,
    )

    real_get_provider = __import__(
        "app.domains.platform.services.routing",
        fromlist=["get_provider"],
    ).get_provider

    def fake_get_provider(provider_code: str):
        if provider_code == "fal_nano_banana":
            raise KeyError("provider_not_found:fal_nano_banana")
        return real_get_provider(provider_code)

    monkeypatch.setattr(
        "app.domains.platform.services.routing.get_provider",
        fake_get_provider,
    )
    service = RoutingService()

    candidates = service.list_candidates(route_group="images", requested_model="nano-banana-2")
    plan = service.plan(
        route_group="images",
        requested_model="nano-banana-2",
        chain=None,
        allow_fallback=True,
    )
    chain = service.default_chain(
        route_group="images",
        requested_model="nano-banana-2",
        allow_fallback=True,
    )

    assert [candidate.provider_code for candidate in candidates] == ["openrouter"]
    assert plan.route_plan == ["openrouter"]
    assert chain == "openrouter"
