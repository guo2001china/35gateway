from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


QWEN_PROVIDERS: dict[str, ProviderConfig] = {
    "qwen_official": ProviderConfig(
        provider_code="qwen_official",
        provider_name="Qwen Official",
        adapter_key="qwen",
        base_url=provider_env("API35_QWEN_OFFICIAL_BASE_URL", "https://dashscope.aliyuncs.com"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_QWEN_OFFICIAL_API_KEY", ""),
        },
    ),
}
