from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


GRSAI_PROVIDERS: dict[str, ProviderConfig] = {
    "grsai_nano_banana": ProviderConfig(
        provider_code="grsai_nano_banana",
        provider_name="GRSAI Nano Banana",
        adapter_key="grsai",
        base_url=provider_env("API35_GRSAI_BASE_URL", "https://grsaiapi.com"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_GRSAI_API_KEY", ""),
            "banana_create_path": provider_env(
                "API35_GRSAI_NANO_BANANA_CREATE_PATH",
                "/v1/draw/nano-banana",
            ),
            "banana_result_path": provider_env(
                "API35_GRSAI_NANO_BANANA_RESULT_PATH",
                "/v1/draw/result",
            ),
            "banana_poll_interval_seconds": provider_env(
                "API35_GRSAI_NANO_BANANA_POLL_INTERVAL_SECONDS",
                "2",
            ),
            "banana_poll_timeout_seconds": provider_env(
                "API35_GRSAI_NANO_BANANA_POLL_TIMEOUT_SECONDS",
                "60",
            ),
        },
    )
}
