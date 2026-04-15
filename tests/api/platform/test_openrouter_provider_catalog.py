from app.core.provider_catalog.openrouter import build_openrouter_providers


def test_openrouter_provider_exists_without_api_key(monkeypatch) -> None:
    mapping = {
        "API35_OPENROUTER_API_KEY": "",
        "API35_OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.openrouter.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_openrouter_providers()

    assert providers["openrouter"].auth_config["api_key"] == ""
    assert providers["openrouter"].base_url == "https://openrouter.ai/api/v1"


def test_openrouter_provider_uses_public_model_and_upstream_alias(monkeypatch) -> None:
    mapping = {
        "API35_OPENROUTER_API_KEY": "or-key",
        "API35_OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.openrouter.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_openrouter_providers()
    openrouter = providers["openrouter"]

    assert openrouter.auth_config["api_key"] == "or-key"
    assert openrouter.adapter_key == "openai"
    assert openrouter.auth_type == "bearer"
    assert not hasattr(openrouter, "models")


def test_openrouter_provider_lane_is_paid(monkeypatch) -> None:
    mapping = {
        "API35_OPENROUTER_API_KEY": "or-key",
        "API35_OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.openrouter.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_openrouter_providers()

    assert providers["openrouter"].lane == "paid"
