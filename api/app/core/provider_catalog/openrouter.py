from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def build_openrouter_providers() -> dict[str, ProviderConfig]:
    api_key = provider_env("API35_OPENROUTER_API_KEY", "")
    return {
        "openrouter": ProviderConfig(
            provider_code="openrouter",
            provider_name="OpenRouter",
            adapter_key="openai",
            base_url=provider_env("API35_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            auth_type="bearer",
            auth_config={
                "api_key": api_key,
            },
        ),
    }


OPENROUTER_PROVIDERS: dict[str, ProviderConfig] = build_openrouter_providers()
