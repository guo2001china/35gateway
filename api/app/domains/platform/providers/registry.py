from __future__ import annotations

from app.domains.platform.providers.base import BaseProviderAdapter
from app.domains.platform.providers.fal import FalAdapter
from app.domains.platform.providers.gateway35m import Gateway35MAdapter
from app.domains.platform.providers.gemini_veo import GeminiVeoAdapter
from app.domains.platform.providers.google import GoogleAdapter
from app.domains.platform.providers.grsai import GRSAIAdapter
from app.domains.platform.providers.ksyun_openai import KsyunOpenAIAdapter
from app.domains.platform.providers.kling import KlingAdapter
from app.domains.platform.providers.minimax import MiniMaxAdapter
from app.domains.platform.providers.openai import OpenAIAdapter
from app.domains.platform.providers.qwen import QwenAdapter
from app.domains.platform.providers.runninghub import RunningHubAdapter
from app.domains.platform.providers.vidu import ViduAdapter
from app.domains.platform.providers.volcengine import VolcengineAdapter
from app.domains.platform.providers.wan import WanAdapter


ADAPTER_REGISTRY: dict[str, type[BaseProviderAdapter]] = {
    "35m": Gateway35MAdapter,
    "fal": FalAdapter,
    "gemini_veo": GeminiVeoAdapter,
    "grsai": GRSAIAdapter,
    "ksyun_openai": KsyunOpenAIAdapter,
    "kling": KlingAdapter,
    "minimax": MiniMaxAdapter,
    "openai": OpenAIAdapter,
    "qwen": QwenAdapter,
    "google": GoogleAdapter,
    "runninghub": RunningHubAdapter,
    "vidu": ViduAdapter,
    "volcengine": VolcengineAdapter,
    "wan": WanAdapter,
}


def _resolve_adapter_key(provider_code: str) -> str:
    if provider_code in ADAPTER_REGISTRY:
        return provider_code

    normalized = provider_code.strip().lower()
    for adapter_key in ADAPTER_REGISTRY:
        if normalized == adapter_key or normalized.startswith(f"{adapter_key}_"):
            return adapter_key

    raise KeyError(f"adapter_not_found:{provider_code}")


def get_adapter(provider_code: str) -> BaseProviderAdapter:
    adapter_key = _resolve_adapter_key(provider_code)
    adapter_cls = ADAPTER_REGISTRY[adapter_key]
    return adapter_cls()
