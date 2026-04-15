from __future__ import annotations

from fastapi import Request

from app.core.config import settings


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1", "testserver"}


def is_local_host(hostname: str) -> bool:
    normalized = hostname.strip().lower()
    return normalized in _LOCAL_HOSTS or normalized.endswith(".localhost")


def _normalize_console_base(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value.rstrip("/")
    normalized = "/" + value.strip("/")
    return normalized.rstrip("/") or "/"


def resolve_console_base_url(request: Request) -> str:
    configured_frontend = settings.web_frontend_url.strip().rstrip("/")
    if configured_frontend:
        return configured_frontend

    configured_console = _normalize_console_base(settings.site_console_url)
    if configured_console:
        return configured_console

    return "/console"


def resolve_console_url(request: Request, path: str = "/") -> str:
    base = resolve_console_base_url(request).rstrip("/")
    normalized_path = "/" if not path or path == "/" else f"/{path.lstrip('/')}"
    if not base or base == "/":
        return normalized_path
    if normalized_path == "/":
        return f"{base}/"
    return f"{base}{normalized_path}"
