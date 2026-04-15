from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


JSON_PAYLOAD = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    auth_identities: Mapped[list["UserAuthIdentity"]] = relationship(back_populates="user")
    provider_accounts: Mapped[list["ProviderAccount"]] = relationship(back_populates="user")
    growth_profile: Mapped["UserGrowthProfile | None"] = relationship(back_populates="user", uselist=False)
    business_events: Mapped[list["BusinessEvent"]] = relationship(back_populates="user")


class UserGrowthProfile(Base):
    __tablename__ = "user_growth_profiles"
    __table_args__ = (
        UniqueConstraint("user_id"),
        Index("idx_user_growth_profiles_acquisition_source", "acquisition_source"),
        Index("idx_user_growth_profiles_first_activated_at", "first_activated_at"),
        Index("idx_user_growth_profiles_first_paid_at", "first_paid_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    first_touch_source: Mapped[str | None] = mapped_column(String(128))
    first_touch_medium: Mapped[str | None] = mapped_column(String(128))
    first_touch_campaign: Mapped[str | None] = mapped_column(String(255))
    first_touch_referrer: Mapped[str | None] = mapped_column(String(1024))
    landing_path: Mapped[str | None] = mapped_column(String(1024))
    last_non_direct_source: Mapped[str | None] = mapped_column(String(128))
    last_non_direct_medium: Mapped[str | None] = mapped_column(String(128))
    last_non_direct_campaign: Mapped[str | None] = mapped_column(String(255))
    acquisition_source: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    customer_motion: Mapped[str] = mapped_column(String(64), nullable=False, default="self_serve")
    customer_segment: Mapped[str | None] = mapped_column(String(64))
    first_activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="growth_profile")


class BusinessEvent(Base):
    __tablename__ = "business_events"
    __table_args__ = (
        Index("idx_business_events_event_name_occurred_at", "event_name", "occurred_at"),
        Index("idx_business_events_user_event_occurred_at", "user_id", "event_name", "occurred_at"),
        Index("idx_business_events_public_model_code_occurred_at", "public_model_code", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    public_model_code: Mapped[str | None] = mapped_column(String(128))
    route_group: Mapped[str | None] = mapped_column(String(64))
    provider_code: Mapped[str | None] = mapped_column(String(128))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    power_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    currency: Mapped[str | None] = mapped_column(String(16))
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    context_payload: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="business_events")


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index(
            "uq_api_keys_system_default_user",
            "user_id",
            unique=True,
            postgresql_where=text("key_kind = 'system_default'"),
            sqlite_where=text("key_kind = 'system_default'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="user_created")
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_plaintext: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")


class UserAuthIdentity(Base):
    __tablename__ = "user_auth_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_union_id: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    password_hash: Mapped[str | None] = mapped_column(String(512))
    profile: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="auth_identities")


class AuthStoreEntry(Base):
    __tablename__ = "auth_store_entries"
    __table_args__ = (
        Index("idx_auth_store_entries_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    store_value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProviderAccount(Base):
    __tablename__ = "provider_accounts"
    __table_args__ = (
        Index("idx_provider_accounts_owner_type_user_id", "owner_type", "user_id"),
        Index("idx_provider_accounts_provider_code", "provider_code"),
        Index("idx_provider_accounts_status", "status"),
        UniqueConstraint("short_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    short_id: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    provider_code: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    routing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    base_url_override: Mapped[str | None] = mapped_column(String(1024))
    credential_payload: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verification_error: Mapped[str | None] = mapped_column(String(512))
    balance_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unsupported")
    balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    balance_currency: Mapped[str | None] = mapped_column(String(16))
    balance_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User | None"] = relationship(back_populates="provider_accounts")


class RedemptionCode(Base):
    __tablename__ = "redemption_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    power_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unused")
    redeemed_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    redeemed_user_no: Mapped[str | None] = mapped_column(String(64))
    redeemed_name: Mapped[str | None] = mapped_column(String(255))
    redeemed_phone: Mapped[str | None] = mapped_column(String(64))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (
        Index("idx_requests_public_model_route_started_at", "public_model_code", "route_group", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    route_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    route_plan: Mapped[list[str]] = mapped_column(JSON_PAYLOAD, nullable=False, default=list)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    record_model_metrics: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_model_code: Mapped[str | None] = mapped_column(String(128))
    route_group: Mapped[str] = mapped_column(String(32), nullable=False)
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_headers: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    request_body: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON_PAYLOAD)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    model_metrics_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderRequest(Base):
    __tablename__ = "provider_requests"
    __table_args__ = (
        Index("idx_provider_requests_started_at", "started_at"),
        Index("idx_provider_requests_provider_started_at", "provider_code", "started_at"),
        Index(
            "idx_provider_requests_provider_execution_model_started_at",
            "provider_code",
            "execution_model_code",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[int | None] = mapped_column(ForeignKey("provider_accounts.id"))
    provider_account_short_id: Mapped[str | None] = mapped_column(String(32))
    provider_account_owner_type: Mapped[str | None] = mapped_column(String(32))
    execution_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    http_status_code: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(512))
    fallback_reason: Mapped[str | None] = mapped_column(String(255))
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_PAYLOAD)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ProviderMetricsHourly(Base):
    __tablename__ = "provider_metrics_hourly"
    __table_args__ = (
        UniqueConstraint("bucket_start", "provider_code", "execution_model_code"),
        Index("idx_provider_metrics_hourly_provider_bucket", "provider_code", "bucket_start"),
        Index("idx_provider_metrics_hourly_execution_model_bucket", "execution_model_code", "bucket_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_sum_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_message: Mapped[str | None] = mapped_column(String(512))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ModelMetricsHourly(Base):
    __tablename__ = "model_metrics_hourly"
    __table_args__ = (
        UniqueConstraint("bucket_start", "public_model_code", "route_group"),
        Index("idx_model_metrics_hourly_public_model_bucket", "public_model_code", "bucket_start"),
        Index("idx_model_metrics_hourly_route_bucket", "route_group", "bucket_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    public_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    route_group: Mapped[str] = mapped_column(String(32), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[int | None] = mapped_column(ForeignKey("provider_accounts.id"))
    provider_account_short_id: Mapped[str | None] = mapped_column(String(32))
    provider_account_owner_type: Mapped[str | None] = mapped_column(String(32))
    public_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_task_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_PAYLOAD)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_metrics_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[int | None] = mapped_column(ForeignKey("provider_accounts.id"))
    provider_account_short_id: Mapped[str | None] = mapped_column(String(32))
    provider_account_owner_type: Mapped[str | None] = mapped_column(String(32))
    public_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    route_group: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    billing_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    billing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    sale_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    sale_currency: Mapped[str | None] = mapped_column(String(16))
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    cost_currency: Mapped[str | None] = mapped_column(String(16))
    margin_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    power_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RechargeOrder(Base):
    __tablename__ = "recharge_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    recharge_order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="CNY")
    power_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    power_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int | None] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformModel(Base):
    __tablename__ = "platform_models"
    __table_args__ = (
        Index("idx_platform_models_category", "category"),
        Index("idx_platform_models_status", "status"),
    )

    model_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    docs_url: Mapped[str | None] = mapped_column(String)
    billing_unit: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="CNY")
    multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("1.11111111"))
    official_price_json: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    provider_cost_json: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    source_url: Mapped[str | None] = mapped_column(String)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformModelRoute(Base):
    __tablename__ = "platform_model_routes"
    __table_args__ = (
        ForeignKeyConstraint(["model_code"], ["platform_models.model_code"], ondelete="CASCADE"),
        Index("idx_platform_model_routes_public_api_visible", "public_api_visible"),
        Index(
            "uq_platform_model_routes_primary_per_model",
            "model_code",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary = 1"),
        ),
    )

    model_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    route_group: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_api_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    endpoints_json: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    api_doc_json: Mapped[dict[str, Any]] = mapped_column(JSON_PAYLOAD, nullable=False, default=dict)
    supported_input_modes_json: Mapped[list[str]] = mapped_column(JSON_PAYLOAD, nullable=False, default=list)
    default_chain_json: Mapped[list[str]] = mapped_column(JSON_PAYLOAD, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformModelProviderBinding(Base):
    __tablename__ = "platform_model_provider_bindings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["model_code", "route_group"],
            ["platform_model_routes.model_code", "platform_model_routes.route_group"],
            ondelete="CASCADE",
        ),
        Index("idx_platform_model_provider_bindings_provider_code", "provider_code"),
        Index("idx_platform_model_provider_bindings_enabled", "enabled"),
    )

    model_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    route_group: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    execution_model_code: Mapped[str] = mapped_column(String(255), nullable=False)
    pricing_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    is_async: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_streaming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
