from __future__ import annotations

from typing import Any

__all__ = ["quote_request"]


def quote_request(*args: Any, **kwargs: Any):
    from app.core.pricing.quote import quote_request as _quote_request

    return _quote_request(*args, **kwargs)
