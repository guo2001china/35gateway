from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def build_google_providers() -> dict[str, ProviderConfig]:
    official_base_url = provider_env("API35_GOOGLE_OFFICIAL_BASE_URL", "https://generativelanguage.googleapis.com")
    openai_base_url = provider_env(
        "API35_GOOGLE_OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    veo_base_url = provider_env(
        "API35_GOOGLE_VEO3_BASE_URL",
        "https://generativelanguage.googleapis.com",
    )
    official_api_key = provider_env("API35_GOOGLE_OFFICIAL_API_KEY") or provider_env("API35_GOOGLE_VEO3_API_KEY", "")
    openai_api_key = (
        provider_env("API35_GOOGLE_OPENAI_API_KEY")
        or provider_env("API35_GOOGLE_OFFICIAL_API_KEY")
        or provider_env("API35_GOOGLE_VEO3_API_KEY", "")
    )
    providers: dict[str, ProviderConfig] = {
        "google_official": ProviderConfig(
            provider_code="google_official",
            provider_name="Google Official",
            adapter_key="google",
            base_url=official_base_url,
            auth_type="api_key",
            auth_config={
                "api_key": official_api_key,
            },
        ),
        "google_openai_compat": ProviderConfig(
            provider_code="google_openai_compat",
            provider_name="Google OpenAI-Compatible",
            adapter_key="openai",
            base_url=openai_base_url,
            auth_type="bearer",
            auth_config={
                "api_key": openai_api_key,
            },
        ),
        "google_veo3": ProviderConfig(
            provider_code="google_veo3",
            provider_name="Google Veo",
            adapter_key="gemini_veo",
            base_url=veo_base_url,
            auth_type="api_key",
            auth_config={
                "api_key": provider_env("API35_GOOGLE_VEO3_API_KEY", ""),
            },
        ),
    }

    return providers


GOOGLE_PROVIDERS: dict[str, ProviderConfig] = build_google_providers()
