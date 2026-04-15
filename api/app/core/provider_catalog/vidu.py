from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


VIDU_PROVIDERS: dict[str, ProviderConfig] = {
    "vidu_official": ProviderConfig(
        provider_code="vidu_official",
        provider_name="Vidu Official",
        adapter_key="vidu",
        base_url=provider_env("API35_VIDU_OFFICIAL_BASE_URL", "https://api.vidu.cn"),
        auth_type="token",
        auth_config={
            "api_key": provider_env("API35_VIDU_OFFICIAL_API_KEY", ""),
        },
    ),
}
