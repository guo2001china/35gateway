from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


OPENAI_PROVIDERS: dict[str, ProviderConfig] = {
    "yunwu_openai": ProviderConfig(
        provider_code="yunwu_openai",
        provider_name="Yunwu OpenAI-Compatible",
        adapter_key="openai",
        base_url=provider_env("API35_YUNWU_OPENAI_BASE_URL", "https://yunwu.1mx.cn"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_YUNWU_OPENAI_API_KEY", ""),
        },
    ),
    "ksyun_openai": ProviderConfig(
        provider_code="ksyun_openai",
        provider_name="Ksyun OpenAI-Compatible",
        adapter_key="ksyun_openai",
        base_url=provider_env("API35_KSYUN_OPENAI_BASE_URL", "https://global-kspmas.ksyun.com/v1"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_KSYUN_OPENAI_API_KEY", ""),
        },
    ),
    "openai_official": ProviderConfig(
        provider_code="openai_official",
        provider_name="OpenAI Official",
        adapter_key="openai",
        base_url=provider_env("API35_OPENAI_OFFICIAL_BASE_URL", "https://api.openai.com"),
        auth_type="bearer",
        auth_config={
            "api_key": provider_env("API35_OPENAI_OFFICIAL_API_KEY", ""),
        },
    ),
}
