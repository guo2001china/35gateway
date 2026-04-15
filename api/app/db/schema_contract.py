from __future__ import annotations

RETAINED_SCHEMA_TABLES: tuple[str, ...] = (
    "api_keys",
    "auth_store_entries",
    "business_events",
    "billing_records",
    "files",
    "platform_model_provider_bindings",
    "platform_model_routes",
    "platform_models",
    "provider_accounts",
    "model_metrics_hourly",
    "provider_metrics_hourly",
    "provider_requests",
    "recharge_orders",
    "redemption_codes",
    "requests",
    "tasks",
    "user_auth_identities",
    "user_growth_profiles",
    "users",
)

RETIRED_SCHEMA_TABLES: tuple[str, ...] = (
    "customer_asset",
    "customer_workflow_card_run_record",
    "customer_workflow_run_record",
    "model_catalog",
    "user_settings",
    "workflow_chat_messages",
    "workflow_recommendation",
)

RETAINED_SCHEMA_TABLE_SET = frozenset(RETAINED_SCHEMA_TABLES)
RETIRED_SCHEMA_TABLE_SET = frozenset(RETIRED_SCHEMA_TABLES)


def is_retained_table(table_name: str | None) -> bool:
    return bool(table_name) and table_name in RETAINED_SCHEMA_TABLE_SET
