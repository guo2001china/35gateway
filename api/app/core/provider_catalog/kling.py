from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


KLING_PROVIDERS: dict[str, ProviderConfig] = {
    "kling_official": ProviderConfig(
        provider_code="kling_official",
        provider_name="Kling Official",
        adapter_key="kling",
        base_url=provider_env("API35_KLING_OFFICIAL_BASE_URL", "https://api-singapore.klingai.com"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_KLING_OFFICIAL_API_KEY", ""),
            "access_key": provider_env("API35_KLING_OFFICIAL_ACCESS_KEY", ""),
            "secret_key": provider_env("API35_KLING_OFFICIAL_SECRET_KEY", ""),
        },
    ),
}
