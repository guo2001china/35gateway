from __future__ import annotations

from typing import Any

from pydantic import Field

from app.api.schemas.common import OpenSchemaModel
from app.api.schemas.auth import GrowthContextPayload


class UserApiKeyCreateRequest(OpenSchemaModel):
    key_name: str = Field(min_length=1, max_length=255)


class UserApiKeyUpdateRequest(OpenSchemaModel):
    key_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=32)


class UserApiKeyResponse(OpenSchemaModel):
    id: int
    key_name: str
    key_kind: str
    key_prefix: str | None = None
    api_key: str | None = None
    status: str
    created_at: str | None = None
    last_used_at: str | None = None


class UserAuthIdentityResponse(OpenSchemaModel):
    provider: str
    email: str | None = None
    phone: str | None = None
    last_login_at: str | None = None


class UserProfileResponse(OpenSchemaModel):
    user_id: int
    user_no: str
    name: str
    balance: str
    status: str
    email: str | None = None
    phone: str | None = None
    identities: list[UserAuthIdentityResponse] = Field(default_factory=list)
    password_login_enabled: bool = False
    password_updated_at: str | None = None
    created_at: str | None = None


class UserProfileUpdateRequest(OpenSchemaModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class UserGrowthContextUpsertRequest(OpenSchemaModel):
    growth_context: GrowthContextPayload


class UserGrowthContextResponse(OpenSchemaModel):
    first_touch_source: str | None = None
    first_touch_medium: str | None = None
    first_touch_campaign: str | None = None
    first_touch_referrer: str | None = None
    landing_path: str | None = None
    last_non_direct_source: str | None = None
    last_non_direct_medium: str | None = None
    last_non_direct_campaign: str | None = None
    acquisition_source: str
    customer_motion: str
    customer_segment: str | None = None
    first_activated_at: str | None = None
    first_paid_at: str | None = None


class UserLogListItemResponse(OpenSchemaModel):
    request_id: str
    created_at: str | None = None
    model: str
    status: str
    power_amount: str | None = None
    duration_ms: int | None = None


class UserLogListResponse(OpenSchemaModel):
    total: int
    page: int
    size: int
    items: list[UserLogListItemResponse] = Field(default_factory=list)


class UserTaskStatsResponse(OpenSchemaModel):
    active_count: int = 0
    pending_billing_count: int = 0
    completed_count: int = 0
    failed_or_waived_count: int = 0


class UserTaskListItemResponse(OpenSchemaModel):
    task_id: str
    request_id: str
    model: str
    route_group: str
    route_type: str
    provider_code: str
    provider_account_id: int | None = None
    provider_account_short_id: str | None = None
    provider_account_owner_type: str | None = None
    provider_task_id: str | None = None
    task_status: str
    billing_status: str | None = None
    result_available: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None


class UserTaskListResponse(OpenSchemaModel):
    total: int
    page: int
    size: int
    summary: UserTaskStatsResponse = Field(default_factory=UserTaskStatsResponse)
    items: list[UserTaskListItemResponse] = Field(default_factory=list)


class UserProviderAttemptResponse(OpenSchemaModel):
    attempt_no: int
    provider_code: str
    provider_account_id: int | None = None
    provider_account_short_id: str | None = None
    provider_account_owner_type: str | None = None
    model_code: str
    provider_request_id: str | None = None
    http_status_code: int | None = None
    status: str
    duration_ms: int | None = None
    fallback_reason: str | None = None
    error_message: str | None = None


class UserTaskSummaryResponse(OpenSchemaModel):
    platform_task_id: str
    provider_code: str
    provider_account_id: int | None = None
    provider_account_short_id: str | None = None
    provider_account_owner_type: str | None = None
    provider_task_id: str | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None


class UserTaskDetailResponse(OpenSchemaModel):
    task_id: str
    request_id: str
    model: str
    route_group: str
    route_type: str
    request_path: str
    provider_code: str
    provider_account_id: int | None = None
    provider_account_short_id: str | None = None
    provider_account_owner_type: str | None = None
    provider_task_id: str | None = None
    task_status: str
    billing_status: str | None = None
    power_amount: str | None = None
    sale_amount: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    result_payload: dict[str, Any] | None = None
    result_urls: list[str] = Field(default_factory=list)
    error_message: str | None = None


class UserLogDetailResponse(OpenSchemaModel):
    request_id: str
    model: str
    route_group: str
    request_path: str
    status: str
    created_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    power_amount: str | None = None
    sale_amount: str | None = None
    request_headers: dict[str, Any] = Field(default_factory=dict)
    request_summary: dict[str, Any] | None = None
    response_summary: dict[str, Any] | None = None
    chain: list[UserProviderAttemptResponse] = Field(default_factory=list)
    task: UserTaskSummaryResponse | None = None
    error_message: str | None = None
