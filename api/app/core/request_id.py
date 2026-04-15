from __future__ import annotations

import uuid


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:24]}"

