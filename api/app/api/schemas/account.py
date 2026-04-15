from __future__ import annotations

from app.api.schemas.common import OpenSchemaModel


class UserContextResponse(OpenSchemaModel):
    user_id: int
    api_key_id: int | None = None
    auth_mode: str


class AccountResponse(OpenSchemaModel):
    user_id: int
    balance: str
    status: str
