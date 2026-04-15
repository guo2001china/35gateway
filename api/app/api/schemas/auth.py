from __future__ import annotations

from pydantic import Field

from app.api.schemas.common import OpenSchemaModel


class GrowthContextPayload(OpenSchemaModel):
    first_touch_source: str | None = Field(default=None, min_length=1, max_length=128)
    first_touch_medium: str | None = Field(default=None, min_length=1, max_length=128)
    first_touch_campaign: str | None = Field(default=None, min_length=1, max_length=255)
    first_touch_referrer: str | None = Field(default=None, min_length=1, max_length=1024)
    landing_path: str | None = Field(default=None, min_length=1, max_length=1024)


class PhoneCodeSendRequest(OpenSchemaModel):
    phone: str = Field(min_length=6, max_length=32)


class PhoneCodeSendResponse(OpenSchemaModel):
    provider: str
    phone: str
    expires_in_seconds: int
    debug_code: str | None = None


class EmailCodeSendRequest(OpenSchemaModel):
    email: str = Field(min_length=6, max_length=255)


class EmailCodeSendResponse(OpenSchemaModel):
    provider: str
    email: str
    expires_in_seconds: int
    debug_code: str | None = None


class PhoneLoginRequest(OpenSchemaModel):
    phone: str = Field(min_length=6, max_length=32)
    code: str = Field(min_length=4, max_length=12)
    growth_context: GrowthContextPayload | None = None


class EmailLoginRequest(OpenSchemaModel):
    email: str = Field(min_length=6, max_length=255)
    code: str = Field(min_length=4, max_length=12)
    growth_context: GrowthContextPayload | None = None


class PasswordLoginRequest(OpenSchemaModel):
    email: str = Field(min_length=6, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    growth_context: GrowthContextPayload | None = None


class PasswordRegisterRequest(OpenSchemaModel):
    email: str = Field(min_length=6, max_length=255)
    code: str = Field(min_length=4, max_length=12)
    password: str = Field(min_length=8, max_length=128)
    growth_context: GrowthContextPayload | None = None


class SessionUserResponse(OpenSchemaModel):
    user_id: int
    user_no: str
    name: str
    status: str
    phone: str | None = None
    email: str | None = None


class PhoneLoginResponse(OpenSchemaModel):
    provider: str
    session_token: str
    expires_in_seconds: int
    user: SessionUserResponse


class EmailLoginResponse(OpenSchemaModel):
    provider: str
    session_token: str
    expires_in_seconds: int
    user: SessionUserResponse


class PasswordLoginResponse(OpenSchemaModel):
    provider: str
    session_token: str
    expires_in_seconds: int
    user: SessionUserResponse


class PasswordRegisterResponse(OpenSchemaModel):
    provider: str
    session_token: str
    expires_in_seconds: int
    user: SessionUserResponse


class SessionMeResponse(OpenSchemaModel):
    auth_mode: str
    provider: str
    user: SessionUserResponse
    issued_at: str | None = None
    last_login_at: str | None = None


class SessionLogoutResponse(OpenSchemaModel):
    revoked: bool
