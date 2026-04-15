from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from app.core.provider_catalog import get_provider
from app.core.provider_catalog.types import ProviderConfig
from app.domains.platform.entities.entities import ProviderAccount
from app.domains.platform.services.provider_accounts import (
    OWNER_TYPE_PLATFORM,
    OWNER_TYPE_USER,
    STATUS_ACTIVE,
)
from app.domains.platform.services.routing import RouteResult


class ProviderAccountRuntimeService:
    def __init__(self, db: Session):
        self.db = db

    def expand_attempts(
        self,
        *,
        user_id: int,
        attempts: list[RouteResult],
    ) -> list[RouteResult]:
        expanded: list[RouteResult] = []
        for attempt in attempts:
            runtime_accounts = self._list_runtime_accounts(
                user_id=user_id,
                provider_code=attempt.provider_code,
            )
            if runtime_accounts:
                expanded.extend(
                    self._route_result_with_account(attempt=attempt, account_row=row)
                    for row in runtime_accounts
                )
                continue

            expanded.append(
                replace(
                    attempt,
                    provider=attempt.provider or get_provider(attempt.provider_code),
                    provider_account_id=None,
                    provider_account_short_id=None,
                    provider_account_owner_type=None,
                )
            )
        return expanded

    def _list_runtime_accounts(
        self,
        *,
        user_id: int,
        provider_code: str,
    ) -> list[ProviderAccount]:
        user_rows = (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.owner_type == OWNER_TYPE_USER,
                ProviderAccount.user_id == user_id,
                ProviderAccount.provider_code == provider_code,
                ProviderAccount.status == STATUS_ACTIVE,
            )
            .order_by(ProviderAccount.priority.asc(), ProviderAccount.id.asc())
            .all()
        )

        platform_query = (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.owner_type == OWNER_TYPE_PLATFORM,
                ProviderAccount.user_id.is_(None),
                ProviderAccount.provider_code == provider_code,
                ProviderAccount.status == STATUS_ACTIVE,
            )
            .order_by(ProviderAccount.priority.asc(), ProviderAccount.id.asc())
        )
        platform_rows = [row for row in platform_query.all() if bool(row.routing_enabled)]

        if platform_rows:
            return [*user_rows, *platform_rows]

        has_any_platform_account = (
            self.db.query(ProviderAccount.id)
            .filter(
                ProviderAccount.owner_type == OWNER_TYPE_PLATFORM,
                ProviderAccount.user_id.is_(None),
                ProviderAccount.provider_code == provider_code,
                ProviderAccount.status != "deleted",
            )
            .first()
            is not None
        )
        if has_any_platform_account:
            return user_rows
        return user_rows

    def resolve_provider(
        self,
        *,
        provider_code: str,
        provider_account_id: int | None,
    ) -> ProviderConfig:
        base_provider = get_provider(provider_code)
        if provider_account_id is None:
            return base_provider
        row = self.db.get(ProviderAccount, provider_account_id)
        if row is None:
            return base_provider
        return self._provider_with_account(provider=base_provider, account_row=row)

    def _route_result_with_account(
        self,
        *,
        attempt: RouteResult,
        account_row: ProviderAccount,
    ) -> RouteResult:
        base_provider = attempt.provider or get_provider(attempt.provider_code)
        effective_provider = self._provider_with_account(
            provider=base_provider,
            account_row=account_row,
        )
        return replace(
            attempt,
            provider=effective_provider,
            provider_account_id=account_row.id,
            provider_account_short_id=account_row.short_id,
            provider_account_owner_type=account_row.owner_type,
        )

    def _provider_with_account(
        self,
        *,
        provider: ProviderConfig,
        account_row: ProviderAccount,
    ) -> ProviderConfig:
        merged_auth_config = dict(provider.auth_config or {})
        merged_auth_config.update(dict(account_row.credential_payload or {}))
        base_url = str(account_row.base_url_override or "").strip() or provider.base_url
        return replace(
            provider,
            base_url=base_url,
            auth_config=merged_auth_config,
        )
