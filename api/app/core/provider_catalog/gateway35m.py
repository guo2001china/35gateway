from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def build_gateway35m_providers() -> dict[str, ProviderConfig]:
    base_url = provider_env(
        "API35_35M_BASE_URL",
        provider_env(
            "GATEWAY_35M_BASE_URL",
            provider_env("API35_GATEWAY_35M_BASE_URL", "https://35m.ai"),
        ),
    ).strip()
    api_key = provider_env(
        "API35_35M_API_KEY",
        provider_env(
            "GATEWAY_35M_API_KEY",
            provider_env("API35_GATEWAY_35M_API_KEY", ""),
        ),
    ).strip()
    if not base_url:
        return {}

    return {
        "35m": ProviderConfig(
            provider_code="35m",
            provider_name="35m.ai",
            adapter_key="35m",
            base_url=base_url,
            auth_type="bearer",
            auth_config={"api_key": api_key},
        )
    }


GATEWAY35M_PROVIDERS: dict[str, ProviderConfig] = build_gateway35m_providers()
