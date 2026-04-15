from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


WAN_PROVIDERS: dict[str, ProviderConfig] = {
    "wan_official": ProviderConfig(
        provider_code="wan_official",
        provider_name="Wan Official",
        adapter_key="wan",
        base_url=provider_env("API35_WAN_OFFICIAL_BASE_URL")
        or provider_env("API35_QWEN_OFFICIAL_BASE_URL")
        or "https://dashscope.aliyuncs.com",
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_WAN_OFFICIAL_API_KEY")
            or provider_env("API35_QWEN_OFFICIAL_API_KEY", ""),
        },
    ),
}
