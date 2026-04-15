from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


MINIMAX_PROVIDERS: dict[str, ProviderConfig] = {
    "minimax_official": ProviderConfig(
        provider_code="minimax_official",
        provider_name="MiniMax Official",
        adapter_key="minimax",
        base_url=provider_env("API35_MINIMAX_OFFICIAL_BASE_URL", "https://api.minimax.io"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_MINIMAX_OFFICIAL_API_KEY", ""),
        },
    ),
}
