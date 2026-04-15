from __future__ import annotations

from .cloudflare_workers_ai import CLOUDFLARE_WORKERS_AI_PROVIDERS
from .deepseek import DEEPSEEK_PROVIDERS
from .fal import FAL_PROVIDERS
from .gateway35m import GATEWAY35M_PROVIDERS
from .google import GOOGLE_PROVIDERS
from .grsai import GRSAI_PROVIDERS
from .kling import KLING_PROVIDERS
from .minimax import MINIMAX_PROVIDERS
from .openai import OPENAI_PROVIDERS
from .openrouter import OPENROUTER_PROVIDERS
from .qwen import QWEN_PROVIDERS
from .runninghub import RUNNINGHUB_PROVIDERS
from .tikhub import TIKHUB_PROVIDERS
from .types import ProviderConfig
from .vidu import VIDU_PROVIDERS
from .volcengine import VOLCENGINE_PROVIDERS
from .wan import WAN_PROVIDERS


PROVIDER_CATALOG: dict[str, ProviderConfig] = {
    **OPENAI_PROVIDERS,
    **OPENROUTER_PROVIDERS,
    **CLOUDFLARE_WORKERS_AI_PROVIDERS,
    **DEEPSEEK_PROVIDERS,
    **GOOGLE_PROVIDERS,
    **GATEWAY35M_PROVIDERS,
    **FAL_PROVIDERS,
    **GRSAI_PROVIDERS,
    **KLING_PROVIDERS,
    **MINIMAX_PROVIDERS,
    **QWEN_PROVIDERS,
    **RUNNINGHUB_PROVIDERS,
    **TIKHUB_PROVIDERS,
    **VIDU_PROVIDERS,
    **VOLCENGINE_PROVIDERS,
    **WAN_PROVIDERS,
}


def get_provider(provider_code: str) -> ProviderConfig:
    provider = PROVIDER_CATALOG.get(provider_code)
    if provider is None:
        raise KeyError(f"provider_not_found:{provider_code}")
    return provider


def list_providers() -> list[ProviderConfig]:
    return list(PROVIDER_CATALOG.values())


__all__ = ["PROVIDER_CATALOG", "ProviderConfig", "get_provider", "list_providers"]
