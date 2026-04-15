from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def build_volcengine_providers() -> dict[str, ProviderConfig]:
    api_key = provider_env("VOLCENGINE_SEEDREAM_API_KEY", "").strip()
    return {
        "volcengine_seedream": ProviderConfig(
            provider_code="volcengine_seedream",
            provider_name="Volcengine Seedream",
            adapter_key="volcengine",
            base_url=provider_env(
                "API35_VOLCENGINE_SEEDREAM_BASE_URL",
                "https://ark.cn-beijing.volces.com/api/v3",
            ),
            auth_type="bearer",
            auth_config={
                "api_key": api_key,
                "images_generate_path": provider_env(
                    "API35_VOLCENGINE_SEEDREAM_IMAGES_GENERATE_PATH",
                    "/images/generations",
                ),
            },
        ),
    }


VOLCENGINE_PROVIDERS: dict[str, ProviderConfig] = build_volcengine_providers()
