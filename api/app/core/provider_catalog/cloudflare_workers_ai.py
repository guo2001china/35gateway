from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def _default_base_url(account_id: str) -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


def build_cloudflare_workers_ai_providers() -> dict[str, ProviderConfig]:
    base_url = provider_env("API35_CLOUDFLARE_WORKERS_AI_BASE_URL", "").strip()
    account_id = provider_env("API35_CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = provider_env("API35_CLOUDFLARE_API_TOKEN", "").strip()
    if not base_url:
        base_url = _default_base_url(account_id or "local")

    return {
        "cloudflare_workers_ai": ProviderConfig(
            provider_code="cloudflare_workers_ai",
            provider_name="Cloudflare Workers AI",
            adapter_key="openai",
            base_url=base_url,
            auth_type="bearer",
            auth_config={
                "api_key": api_token,
            },
        ),
    }


CLOUDFLARE_WORKERS_AI_PROVIDERS: dict[str, ProviderConfig] = build_cloudflare_workers_ai_providers()
