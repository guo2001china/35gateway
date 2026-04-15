from __future__ import annotations

from pydantic import Field

from app.api.schemas.common import OpenSchemaModel


class ProviderAccountAuthFieldResponse(OpenSchemaModel):
    field_name: str
    label: str
    required: bool
    secret: bool = True


class ProviderAccountProviderOptionResponse(OpenSchemaModel):
    provider_code: str
    provider_name: str
    supports_balance_sync: bool = False
    auth_fields: list[ProviderAccountAuthFieldResponse] = Field(default_factory=list)


class ProviderAccountResponse(OpenSchemaModel):
    id: int
    short_id: str
    owner_type: str
    user_id: int | None = None
    provider_code: str
    provider_name: str
    display_name: str
    status: str
    routing_enabled: bool
    priority: int
    base_url_override: str | None = None
    verification_status: str
    last_verified_at: str | None = None
    last_verification_error: str | None = None
    balance_status: str
    balance_amount: str | None = None
    balance_currency: str | None = None
    balance_updated_at: str | None = None
    notes: str | None = None
    supports_balance_sync: bool = False


class ProviderAccountCreateRequest(OpenSchemaModel):
    provider_code: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    base_url_override: str | None = Field(default=None, max_length=1024)
    credential_payload: dict[str, str] = Field(default_factory=dict)
    status: str = Field(default="active", min_length=1, max_length=32)
    routing_enabled: bool = True
    priority: int = Field(default=100, ge=0, le=100000)
    notes: str | None = Field(default=None, max_length=1024)


class ProviderAccountUpdateRequest(OpenSchemaModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url_override: str | None = Field(default=None, max_length=1024)
    credential_payload: dict[str, str] | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    routing_enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100000)
    notes: str | None = Field(default=None, max_length=1024)
