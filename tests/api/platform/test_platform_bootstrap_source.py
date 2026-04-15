from __future__ import annotations

import json
from pathlib import Path

from app.domains.platform.services.platform_bootstrap_source import build_platform_bootstrap


def _load_committed_payload() -> dict[str, object]:
    payload_path = (
        Path(__file__).resolve().parents[3]
        / "api"
        / "app"
        / "domains"
        / "platform"
        / "services"
        / "platform_bootstrap_data.json"
    )
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _enabled_binding_providers(bootstrap, public_model_code: str, route_group: str) -> list[str]:
    return [
        row.provider_code
        for row in bootstrap.provider_bindings
        if row.public_model_code == public_model_code and row.route_group == route_group and row.enabled
    ]


def _assert_relative_order(actual: list[str], *expected_codes: str) -> None:
    missing = [code for code in expected_codes if code not in actual]
    assert not missing, f"missing expected codes from chain: {missing}"
    positions = [actual.index(code) for code in expected_codes]
    assert positions == sorted(positions), f"unexpected order: actual={actual}, expected={expected_codes}"


def test_platform_bootstrap_source_loads_expected_bootstrap_payload() -> None:
    bootstrap = build_platform_bootstrap()

    assert bootstrap.models
    assert bootstrap.routes
    assert bootstrap.provider_bindings
    assert {"text", "image", "video", "audio"}.issubset({row.category for row in bootstrap.models})
    assert {
        "gpt-5.4",
        "DeepSeek-V3.2",
        "doubao-seedream-5.0-lite",
        "seedance-2.0-fast",
        "veo-3.1-fast",
        "speech-2.8-hd",
    }.issubset({row.public_model_code for row in bootstrap.models})

    assert len({row.public_model_code for row in bootstrap.models}) == len(bootstrap.models)
    assert len({(row.public_model_code, row.route_group) for row in bootstrap.routes}) == len(bootstrap.routes)
    assert (
        len({(row.public_model_code, row.route_group, row.provider_code) for row in bootstrap.provider_bindings})
        == len(bootstrap.provider_bindings)
    )

    for route in bootstrap.routes:
        enabled_providers = _enabled_binding_providers(bootstrap, route.public_model_code, route.route_group)
        if route.public_api_visible and enabled_providers:
            assert route.default_chain_json, (
                f"public route missing default chain: {(route.public_model_code, route.route_group)!r}"
            )
        assert set(route.default_chain_json).issubset(set(enabled_providers)), (
            f"default chain not covered by enabled bindings: {(route.public_model_code, route.route_group)!r}"
        )

    deepseek_route = next(
        row for row in bootstrap.routes if row.public_model_code == "DeepSeek-V3.2" and row.route_group == "openai"
    )
    assert deepseek_route.supported_input_modes_json == ["chat"]
    assert deepseek_route.default_chain_json == ["35m"]

    banana_35m_binding = next(
        row
        for row in bootstrap.provider_bindings
        if row.public_model_code == "nano-banana-2"
        and row.route_group == "banana"
        and row.provider_code == "35m"
    )
    assert banana_35m_binding.execution_model_code == "gemini-3.1-flash-image-preview"
    assert banana_35m_binding.pricing_strategy == "image_banana_fixed_resolution"
    assert banana_35m_binding.is_streaming is False

    gpt54_model = next(row for row in bootstrap.models if row.public_model_code == "gpt-5.4")
    assert gpt54_model.billing_unit == "token"
    assert gpt54_model.provider_cost_json["input_per_1m_tokens"]

    gpt54_route = next(
        row for row in bootstrap.routes if row.public_model_code == "gpt-5.4" and row.route_group == "openai"
    )
    assert gpt54_route.default_chain_json == ["35m"]

    gpt54_35m_binding = next(
        row
        for row in bootstrap.provider_bindings
        if row.public_model_code == "gpt-5.4"
        and row.route_group == "openai"
        and row.provider_code == "35m"
    )
    assert gpt54_35m_binding.execution_model_code == "gpt-5.4"
    assert gpt54_35m_binding.pricing_strategy == "text_tokens"

    seedance_fast_model = next(row for row in bootstrap.models if row.public_model_code == "seedance-2.0-fast")
    assert seedance_fast_model.billing_unit == "second"
    assert seedance_fast_model.provider_cost_json["per_second"] == "1.69330000"

    seedance_fast_route = next(
        row for row in bootstrap.routes if row.public_model_code == "seedance-2.0-fast" and row.route_group == "seedance"
    )
    assert seedance_fast_route.default_chain_json == ["35m"]
    assert seedance_fast_route.supported_input_modes_json == ["text", "image"]

    seedance_binding = next(
        row
        for row in bootstrap.provider_bindings
        if row.public_model_code == "seedance-2.0-fast"
        and row.route_group == "seedance"
        and row.provider_code == "35m"
    )
    assert seedance_binding.execution_model_code == "seedance-2.0-fast"
    assert seedance_binding.pricing_strategy == "video_seedance"


def test_platform_bootstrap_payload_matches_committed_json_shape() -> None:
    payload = _load_committed_payload()

    assert isinstance(payload.get("models"), list)
    assert isinstance(payload.get("routes"), list)
    assert isinstance(payload.get("provider_bindings"), list)
    assert "pricing" not in payload

    first_model = payload["models"][0]
    assert "billing_unit" in first_model
    assert "provider_cost_json" in first_model
    assert "pricing_model_code" not in first_model

    first_route = payload["routes"][0]
    assert "default_chain_json" in first_route
    assert "default_provider_chain_json" not in first_route

    first_binding = payload["provider_bindings"][0]
    assert "execution_model_code" in first_binding
    assert "pricing_strategy" in first_binding
    assert "pricing_model_code" not in first_binding
    assert "billing_unit" not in first_binding
