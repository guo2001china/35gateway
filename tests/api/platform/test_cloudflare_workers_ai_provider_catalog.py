from app.core.provider_catalog.cloudflare_workers_ai import build_cloudflare_workers_ai_providers


def test_cloudflare_workers_ai_provider_exists_without_credentials(monkeypatch) -> None:
    mapping = {
        "API35_CLOUDFLARE_ACCOUNT_ID": "",
        "API35_CLOUDFLARE_WORKERS_AI_BASE_URL": "",
        "API35_CLOUDFLARE_API_TOKEN": "",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.cloudflare_workers_ai.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_cloudflare_workers_ai_providers()

    provider = providers["cloudflare_workers_ai"]
    assert provider.auth_config["api_key"] == ""
    assert provider.base_url == "https://api.cloudflare.com/client/v4/accounts/local/ai/v1"


def test_cloudflare_workers_ai_provider_uses_local_endpoint_fallback(monkeypatch) -> None:
    mapping = {
        "API35_CLOUDFLARE_API_TOKEN": "cf-token",
        "API35_CLOUDFLARE_ACCOUNT_ID": "",
        "API35_CLOUDFLARE_WORKERS_AI_BASE_URL": "",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.cloudflare_workers_ai.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_cloudflare_workers_ai_providers()

    assert providers["cloudflare_workers_ai"].base_url == "https://api.cloudflare.com/client/v4/accounts/local/ai/v1"


def test_cloudflare_workers_ai_provider_uses_explicit_base_url(monkeypatch) -> None:
    mapping = {
        "API35_CLOUDFLARE_WORKERS_AI_BASE_URL": "https://example.com/cf-ai",
        "API35_CLOUDFLARE_API_TOKEN": "cf-token",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.cloudflare_workers_ai.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_cloudflare_workers_ai_providers()
    provider = providers["cloudflare_workers_ai"]

    assert provider.auth_config["api_key"] == "cf-token"
    assert provider.base_url == "https://example.com/cf-ai"
    assert provider.adapter_key == "openai"
    assert provider.auth_type == "bearer"
    assert not hasattr(provider, "models")


def test_cloudflare_workers_ai_provider_uses_account_id_fallback(monkeypatch) -> None:
    mapping = {
        "API35_CLOUDFLARE_ACCOUNT_ID": "acct_123",
        "API35_CLOUDFLARE_API_TOKEN": "cf-token",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.cloudflare_workers_ai.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_cloudflare_workers_ai_providers()

    assert providers["cloudflare_workers_ai"].base_url == "https://api.cloudflare.com/client/v4/accounts/acct_123/ai/v1"


def test_cloudflare_workers_ai_provider_lane_is_paid(monkeypatch) -> None:
    mapping = {
        "API35_CLOUDFLARE_WORKERS_AI_BASE_URL": "https://example.com/cf-ai",
        "API35_CLOUDFLARE_API_TOKEN": "cf-token",
    }
    monkeypatch.setattr(
        "app.core.provider_catalog.cloudflare_workers_ai.provider_env",
        lambda name, default="": mapping.get(name, default),
    )

    providers = build_cloudflare_workers_ai_providers()

    assert providers["cloudflare_workers_ai"].lane == "paid"
