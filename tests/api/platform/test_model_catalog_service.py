from __future__ import annotations

from decimal import Decimal

from app.domains.platform.services.model_catalog_service import ModelCatalogService
from app.domains.platform.services.platform_config_snapshot import (
    PlatformConfigSnapshot,
    PlatformModelProviderBindingSnapshot,
    PlatformModelRouteSnapshot,
    PlatformModelSnapshot,
)


class _FakeMetricsService:
    def parse_window(self, window: str | None) -> str:
        return window or "24h"

    def default_metrics(self, window: str | None = None) -> dict[str, object]:
        return {
            "window": window or "24h",
            "sample_count": 0,
            "success_count": 0,
            "success_rate": None,
            "sample_ready": False,
            "latency": {"avg_ms": None, "p50_ms": None, "p95_ms": None, "sample_count": 0},
        }

    def provider_metrics(self, model_code: str, window: str | None) -> dict[str, dict[str, object]]:
        return {}


def _model(model_code: str, *, category: str, billing_unit: str) -> PlatformModelSnapshot:
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
        provider_cost={"base": "1.0"},
        notes="",
        source_url="https://example.com/pricing",
        last_verified_at=None,
    )


def _single_route_snapshot(
    *,
    model: PlatformModelSnapshot,
    route_group: str,
    default_chain: tuple[str, ...],
    bindings: tuple[PlatformModelProviderBindingSnapshot, ...],
    supported_input_modes: tuple[str, ...],
) -> PlatformConfigSnapshot:
    route = PlatformModelRouteSnapshot(
        public_model_code=model.public_model_code,
        route_group=route_group,
        is_primary=True,
        public_api_visible=True,
        endpoints={"create": f"POST /v1/{model.public_model_code}"},
        api_doc={},
        supported_input_modes=supported_input_modes,
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
    model = _model("gpt-5.4", category="text", billing_unit="token")
    return _single_route_snapshot(
        model=model,
        route_group="openai",
        default_chain=("yunwu_openai", "openai_official", "ksyun_openai"),
        bindings=(
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="yunwu_openai",
                enabled=True,
                execution_model_code="gpt-5.4",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="openai_official",
                enabled=True,
                execution_model_code="gpt-5.4",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="ksyun_openai",
                enabled=True,
                execution_model_code="mog-3-global",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
        ),
        supported_input_modes=("chat",),
    )


def _gemini_snapshot() -> PlatformConfigSnapshot:
    model = _model("gemini-3.1-pro-preview", category="text", billing_unit="token")
    return _single_route_snapshot(
        model=model,
        route_group="openai",
        default_chain=("yunwu_openai", "google_openai_compat", "ksyun_openai"),
        bindings=(
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="yunwu_openai",
                enabled=True,
                execution_model_code="gemini-3.1-pro-preview",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="google_openai_compat",
                enabled=True,
                execution_model_code="gemini-3.1-pro-preview",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
            PlatformModelProviderBindingSnapshot(
                public_model_code=model.public_model_code,
                route_group="openai",
                provider_code="ksyun_openai",
                enabled=True,
                execution_model_code="mgg-8-global",
                pricing_strategy="text_tokens",
                is_async=False,
                is_streaming=True,
            ),
        ),
        supported_input_modes=("chat",),
    )


def _vidu_snapshot() -> PlatformConfigSnapshot:
    pro = _model("viduq3-pro", category="video", billing_unit="credit")
    turbo = _model("viduq3-turbo", category="video", billing_unit="credit")
    routes = {
        ("viduq3-pro", "vidu"): PlatformModelRouteSnapshot(
            public_model_code="viduq3-pro",
            route_group="vidu",
            is_primary=True,
            public_api_visible=True,
            endpoints={"create": "POST /v1/viduq3-pro"},
            api_doc={},
            supported_input_modes=("text", "image", "start_end"),
            default_chain=("vidu_official",),
        ),
        ("viduq3-turbo", "vidu"): PlatformModelRouteSnapshot(
            public_model_code="viduq3-turbo",
            route_group="vidu",
            is_primary=True,
            public_api_visible=True,
            endpoints={"create": "POST /v1/viduq3-turbo"},
            api_doc={},
            supported_input_modes=("text", "image", "start_end"),
            default_chain=("vidu_official",),
        ),
    }
    bindings = {
        ("viduq3-pro", "vidu"): (
            PlatformModelProviderBindingSnapshot(
                public_model_code="viduq3-pro",
                route_group="vidu",
                provider_code="vidu_official",
                enabled=True,
                execution_model_code="viduq3-pro",
                pricing_strategy="video_vidu",
                is_async=True,
                is_streaming=False,
            ),
        ),
        ("viduq3-turbo", "vidu"): (
            PlatformModelProviderBindingSnapshot(
                public_model_code="viduq3-turbo",
                route_group="vidu",
                provider_code="vidu_official",
                enabled=True,
                execution_model_code="viduq3-turbo",
                pricing_strategy="video_vidu",
                is_async=True,
                is_streaming=False,
            ),
        ),
    }
    routes_by_model = {
        "viduq3-pro": (routes[("viduq3-pro", "vidu")],),
        "viduq3-turbo": (routes[("viduq3-turbo", "vidu")],),
    }
    return PlatformConfigSnapshot(
        models={"viduq3-pro": pro, "viduq3-turbo": turbo},
        routes=routes,
        routes_by_model=routes_by_model,
        public_routes_by_model=routes_by_model,
        bindings_by_route=bindings,
    )


def test_list_model_providers_exposes_lane() -> None:
    service = ModelCatalogService(db=None)  # type: ignore[arg-type]
    service.metrics_service = _FakeMetricsService()
    service._snapshot = _gpt54_snapshot  # type: ignore[method-assign]

    providers = service.list_model_providers("gpt-5.4", "24h")

    assert len(providers) == 3
    assert [item["provider_code"] for item in providers] == [
        "yunwu_openai",
        "openai_official",
        "ksyun_openai",
    ]
    assert all(item["lane"] == "paid" for item in providers)


def test_model_detail_providers_expose_lane() -> None:
    service = ModelCatalogService(db=None)  # type: ignore[arg-type]
    service.metrics_service = _FakeMetricsService()
    service._snapshot = _gpt54_snapshot  # type: ignore[method-assign]

    detail = service.get_model_detail("gpt-5.4", "24h")

    assert detail["providers"]
    assert all("lane" in provider for provider in detail["providers"])


def test_gemini_preview_models_expose_ksyun_provider(monkeypatch) -> None:
    service = ModelCatalogService(db=None)  # type: ignore[arg-type]
    service.metrics_service = _FakeMetricsService()
    monkeypatch.setattr(service, "_snapshot", _gemini_snapshot)

    providers = service.list_model_providers("gemini-3.1-pro-preview", "24h")

    assert [item["provider_code"] for item in providers] == [
        "yunwu_openai",
        "google_openai_compat",
        "ksyun_openai",
    ]


def test_vidu_q3_models_expose_vidu_official_provider() -> None:
    service = ModelCatalogService(db=None)  # type: ignore[arg-type]
    service.metrics_service = _FakeMetricsService()
    service._snapshot = _vidu_snapshot  # type: ignore[method-assign]

    providers = service.list_model_providers("viduq3-pro", "24h")
    detail = service.get_model_detail("viduq3-turbo", "24h")

    assert {item["provider_code"] for item in providers} == {"vidu_official"}
    assert detail["route_group"] == "vidu"
    assert detail["supported_input_modes"] == ["text", "image", "start_end"]
