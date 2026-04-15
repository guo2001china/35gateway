from __future__ import annotations

import os
from functools import lru_cache

from app.core.config import ENV_FILE


@lru_cache(maxsize=1)
def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed = value.strip()
        if len(parsed) >= 2 and parsed[0] == parsed[-1] and parsed[0] in {'"', "'"}:
            parsed = parsed[1:-1]
        values[key.strip()] = parsed
    return values


def provider_env(name: str, default: str = "") -> str:
    runtime_value = os.getenv(name)
    if runtime_value:
        return runtime_value
    env_file_value = _load_env_file().get(name)
    if env_file_value:
        return env_file_value
    return default
