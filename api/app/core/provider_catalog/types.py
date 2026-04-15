from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    provider_code: str
    provider_name: str
    adapter_key: str
    base_url: str
    auth_type: str
    auth_config: dict[str, str]
    lane: str = "paid"
