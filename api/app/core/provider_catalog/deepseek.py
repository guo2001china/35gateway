from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


DEEPSEEK_PROVIDERS: dict[str, ProviderConfig] = {
    "deepseek_official": ProviderConfig(
        provider_code="deepseek_official",
        provider_name="DeepSeek Official",
        adapter_key="openai",
        base_url=provider_env("API35_DEEPSEEK_OFFICIAL_BASE_URL", "https://api.deepseek.com"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_DEEPSEEK_OFFICIAL_API_KEY", ""),
        },
    ),
}
