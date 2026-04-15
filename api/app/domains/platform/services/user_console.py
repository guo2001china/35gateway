from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.security import API_KEY_PREFIX, generate_api_key, hash_api_key
from app.domains.platform.entities.entities import ApiKey, BillingRecord, ProviderRequest, Request, Task, User, UserAuthIdentity
from app.domains.platform.services.auth_sessions import PASSWORD_AUTH_PROVIDER
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.system_api_keys import USER_CREATED_KEY_KIND, SystemApiKeyService
from app.domains.platform.services.task_control import ACTIVE_TASK_STATUSES


class UserConsoleService:
    _HEADER_ALLOWLIST = {
        "x-api35-chain",
        "x-api35-fallback",
    }

    def __init__(self, db: Session):
        self.db = db

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def _request_model_expr(self):
        return func.coalesce(
            Request.public_model_code,
            cast(Request.request_body["model"].as_string(), String),
        )

    def list_api_keys(self, *, user_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(ApiKey)
            .filter(ApiKey.user_id == user_id, ApiKey.status != "deleted")
            .order_by(
                ApiKey.key_kind.asc(),
                ApiKey.id.desc(),
            )
            .all()
        )
        return [self._serialize_api_key(row) for row in rows]

    def create_api_key(self, *, user_id: int, key_name: str) -> dict[str, Any]:
        self._get_user(user_id)
        raw_key = generate_api_key()
        row = ApiKey(
            user_id=user_id,
            key_name=key_name,
            key_kind=USER_CREATED_KEY_KIND,
            key_hash=hash_api_key(raw_key),
            key_plaintext=raw_key,
            status="active",
        )
        self.db.add(row)
        self.db.flush()
        BusinessTrackingService(self.db).record_event(
            user_id=user_id,
            event_name="api_key_created",
            context_payload={
                "api_key_id": row.id,
                "key_kind": row.key_kind,
                "key_name_length": len(key_name),
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_api_key(row, include_plaintext=True)

    def reveal_api_key(self, *, user_id: int, api_key_id: int) -> dict[str, Any]:
        row = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="api_key_not_found")
        return self._serialize_api_key(row, include_plaintext=True)

    def update_api_key(
        self,
        *,
        user_id: int,
        api_key_id: int,
        key_name: str | None,
        status: str | None,
    ) -> dict[str, Any]:
        row = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="api_key_not_found")
        SystemApiKeyService(self.db).assert_user_managed(row)
        if key_name is None and status is None:
            raise HTTPException(status_code=422, detail="empty_update_payload")

        if key_name is not None:
            row.key_name = key_name
        if status is not None:
            row.status = status

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_api_key(row)

    def delete_api_key(self, *, user_id: int, api_key_id: int) -> dict[str, Any]:
        row = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="api_key_not_found")
        SystemApiKeyService(self.db).assert_user_managed(row)
        row.status = "deleted"
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_api_key(row)

    def get_profile(self, *, user_id: int) -> dict[str, Any]:
        user = self._get_user(user_id)
        identities = self._list_identities(user_id)
        email = next((identity.email for identity in identities if identity.email), None)
        phone = next((identity.phone for identity in identities if identity.phone), None)
        password_identity = next(
            (
                identity
                for identity in identities
                if identity.provider == PASSWORD_AUTH_PROVIDER and identity.password_hash
            ),
            None,
        )
        return {
            "user_id": user.id,
            "user_no": user.user_no,
            "name": user.name,
            "balance": str(user.balance),
            "status": user.status,
            "email": email,
            "phone": phone,
            "identities": [self._serialize_identity(identity) for identity in identities],
            "password_login_enabled": password_identity is not None,
            "password_updated_at": (
                self._serialize_datetime(password_identity.password_updated_at)
                if password_identity is not None and password_identity.password_updated_at is not None
                else None
            ),
            "created_at": self._serialize_datetime(user.created_at),
        }

    def update_profile(self, *, user_id: int, name: str | None) -> dict[str, Any]:
        user = self._get_user(user_id)
        if name is None:
            raise HTTPException(status_code=422, detail="empty_update_payload")
        user.name = name
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self.get_profile(user_id=user_id)

    def list_logs(self, *, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        total, rows = self.list_logs_paginated(user_id=user_id, page=1, size=limit)
        del total
        return rows

    def list_billing_records_paginated(
        self,
        *,
        user_id: int,
        page: int = 1,
        size: int = 50,
        status: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        if page < 1:
            raise HTTPException(status_code=422, detail="invalid_page")
        if size < 1 or size > 100:
            raise HTTPException(status_code=422, detail="invalid_page_size")

        query = (
            self.db.query(
                BillingRecord.id,
                BillingRecord.public_model_code,
                BillingRecord.provider_code,
                BillingRecord.route_group,
                BillingRecord.billing_unit,
                BillingRecord.sale_amount,
                BillingRecord.power_amount,
                BillingRecord.status,
                BillingRecord.created_at,
                Request.request_id.label("request_log_id"),
            )
            .join(Request, Request.id == BillingRecord.request_id)
            .filter(BillingRecord.user_id == user_id)
        )
        if status:
            query = query.filter(BillingRecord.status == status)
        if model:
            query = query.filter(BillingRecord.public_model_code.ilike(f"%{model}%"))
        if request_id:
            query = query.filter(Request.request_id.ilike(f"%{request_id}%"))

        total = query.count()
        rows = (
            query.order_by(BillingRecord.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return total, [
            {
                "request_id": row.request_log_id,
                "created_at": self._serialize_datetime(row.created_at),
                "model": self._resolve_public_model_code(
                    route_group=row.route_group,
                    model_code=row.public_model_code,
                ),
                "provider_code": row.provider_code,
                "route_group": row.route_group,
                "billing_unit": row.billing_unit,
                "sale_amount": str(row.sale_amount) if row.sale_amount is not None else None,
                "power_amount": str(row.power_amount) if row.power_amount is not None else None,
                "status": row.status,
            }
            for row in rows
        ]

    def list_tasks_paginated(
        self,
        *,
        user_id: int,
        page: int = 1,
        size: int = 50,
        status: str | None = None,
        model: str | None = None,
        query: str | None = None,
    ) -> tuple[int, dict[str, int], list[dict[str, Any]]]:
        if page < 1:
            raise HTTPException(status_code=422, detail="invalid_page")
        if size < 1 or size > 100:
            raise HTTPException(status_code=422, detail="invalid_page_size")

        request_model_expr = self._request_model_expr()
        task_query = (
            self.db.query(
                Task.id,
                Task.platform_task_id,
                Task.provider_code,
                Task.provider_account_id,
                Task.provider_account_short_id,
                Task.provider_account_owner_type,
                Task.public_model_code,
                Task.provider_task_id,
                Task.status.label("task_status"),
                Task.result_payload,
                Task.created_at,
                Task.updated_at,
                Task.finished_at,
                Request.id.label("request_row_id"),
                Request.request_id.label("request_log_id"),
                Request.route_group,
                request_model_expr.label("request_model"),
            )
            .join(Request, Task.request_id == Request.id)
            .filter(Request.user_id == user_id)
        )
        if status:
            task_query = task_query.filter(Task.status == status)
        if model:
            task_query = task_query.filter(
                or_(
                    request_model_expr.ilike(f"%{model}%"),
                    Task.public_model_code.ilike(f"%{model}%"),
                )
            )
        if query:
            task_query = task_query.filter(
                or_(
                    Task.platform_task_id.ilike(f"%{query}%"),
                    Request.request_id.ilike(f"%{query}%"),
                )
            )

        total = task_query.count()
        rows = (
            task_query.order_by(Task.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        request_row_ids = [row.request_row_id for row in rows]
        billing_map = self._latest_billing_records_by_request_id(request_row_ids)
        items = [
            self._serialize_task_list_row(row, billing_record=billing_map.get(row.request_row_id))
            for row in rows
        ]
        return total, self._task_stats(user_id=user_id), items

    def list_logs_paginated(
        self,
        *,
        user_id: int,
        page: int = 1,
        size: int = 50,
        status: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        if page < 1:
            raise HTTPException(status_code=422, detail="invalid_page")
        if size < 1 or size > 100:
            raise HTTPException(status_code=422, detail="invalid_page_size")

        request_model_expr = self._request_model_expr()
        query = self.db.query(
            Request.id,
            Request.request_id,
            Request.route_group,
            request_model_expr.label("request_model"),
            Request.status,
            Request.started_at,
            Request.duration_ms,
        ).filter(Request.user_id == user_id)
        if status:
            query = query.filter(Request.status == status)
        if model:
            query = query.filter(request_model_expr.ilike(f"%{model}%"))
        if request_id:
            query = query.filter(Request.request_id.ilike(f"%{request_id}%"))

        total = query.count()
        rows = (
            query.order_by(Request.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        if not rows:
            return total, []

        request_row_ids = [row.id for row in rows]
        billing_map = self._latest_power_amount_by_request_id(request_row_ids)
        provider_map = self._provider_models_by_request_id(request_row_ids)
        return total, [
            {
                "request_id": row.request_id,
                "created_at": self._serialize_datetime(row.started_at),
                "model": self._resolve_model(
                    route_group=row.route_group,
                    request_model=row.request_model,
                    provider_rows=provider_map.get(row.id, []),
                ),
                "status": row.status,
                "power_amount": billing_map.get(row.id),
                "duration_ms": row.duration_ms,
            }
            for row in rows
        ]

    def get_task_detail(self, *, user_id: int, task_id: str) -> dict[str, Any]:
        row = (
            self.db.query(Task, Request)
            .join(Request, Task.request_id == Request.id)
            .filter(Task.platform_task_id == task_id, Request.user_id == user_id)
            .order_by(Task.id.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="task_not_found")

        task, request_log = row
        billing_record = self._latest_billing_record(request_log.id)
        provider_rows = (
            self.db.query(ProviderRequest)
            .filter(ProviderRequest.request_id == request_log.id)
            .order_by(ProviderRequest.attempt_no.asc(), ProviderRequest.id.asc())
            .all()
        )
        result_payload = self._build_response_summary(row=request_log, task=task)
        return {
            "task_id": task.platform_task_id,
            "request_id": request_log.request_id,
            "model": self._resolve_model(
                route_group=request_log.route_group,
                request_model=self._request_model_from_body(request_log.request_body),
                provider_rows=[task.public_model_code],
            ),
            "route_group": request_log.route_group,
            "route_type": self._route_type(request_log.route_group),
            "request_path": request_log.request_path,
            "provider_code": task.provider_code,
            "provider_account_id": task.provider_account_id,
            "provider_account_short_id": task.provider_account_short_id,
            "provider_account_owner_type": task.provider_account_owner_type,
            "provider_task_id": task.provider_task_id,
            "task_status": task.status,
            "billing_status": billing_record.status if billing_record is not None else None,
            "power_amount": self._serialize_power_amount(billing_record),
            "sale_amount": str(billing_record.sale_amount) if billing_record is not None and billing_record.sale_amount is not None else None,
            "created_at": self._serialize_datetime(task.created_at),
            "updated_at": self._serialize_datetime(task.updated_at),
            "finished_at": self._serialize_datetime(task.finished_at),
            "result_payload": result_payload,
            "result_urls": self._extract_result_urls(result_payload),
            "error_message": self._build_error_message(row=request_log, provider_rows=provider_rows),
        }

    def get_log_detail(self, *, user_id: int, request_id: str) -> dict[str, Any]:
        row = (
            self.db.query(Request)
            .filter(Request.request_id == request_id, Request.user_id == user_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="request_not_found")

        provider_rows = (
            self.db.query(ProviderRequest)
            .filter(ProviderRequest.request_id == row.id)
            .order_by(ProviderRequest.attempt_no.asc(), ProviderRequest.id.asc())
            .all()
        )
        billing_record = self._latest_billing_record(row.id)
        task = (
            self.db.query(Task)
            .filter(Task.request_id == row.id)
            .order_by(Task.id.desc())
            .first()
        )

        return {
            "request_id": row.request_id,
            "model": self._resolve_model(
                route_group=row.route_group,
                request_model=self._request_model_from_body(row.request_body),
                provider_rows=provider_rows,
            ),
            "route_group": row.route_group,
            "request_path": row.request_path,
            "status": row.status,
            "created_at": self._serialize_datetime(row.started_at),
            "finished_at": self._serialize_datetime(row.ended_at),
            "duration_ms": row.duration_ms,
            "power_amount": self._serialize_power_amount(billing_record),
            "sale_amount": str(billing_record.sale_amount) if billing_record is not None and billing_record.sale_amount is not None else None,
            "request_headers": self._whitelist_headers(row.request_headers),
            "request_summary": row.request_body,
            "response_summary": self._build_response_summary(row=row, task=task),
            "chain": [self._serialize_provider_row(item) for item in provider_rows],
            "task": self._serialize_task(task) if task is not None else None,
            "error_message": self._build_error_message(row=row, provider_rows=provider_rows),
        }

    def _get_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        return user

    def _list_identities(self, user_id: int) -> list[UserAuthIdentity]:
        return (
            self.db.query(UserAuthIdentity)
            .filter(UserAuthIdentity.user_id == user_id)
            .order_by(UserAuthIdentity.id.asc())
            .all()
        )

    def _serialize_identity(self, identity: UserAuthIdentity) -> dict[str, Any]:
        return {
            "provider": identity.provider,
            "email": identity.email,
            "phone": identity.phone,
            "last_login_at": self._serialize_datetime(identity.last_login_at),
        }

    def _serialize_api_key(self, row: ApiKey, *, include_plaintext: bool = False) -> dict[str, Any]:
        return {
            "id": row.id,
            "key_name": row.key_name,
            "key_kind": row.key_kind,
            "key_prefix": self._key_prefix(row.key_plaintext),
            "api_key": row.key_plaintext if include_plaintext else None,
            "status": row.status,
            "created_at": self._serialize_datetime(row.created_at),
            "last_used_at": self._serialize_datetime(row.last_used_at),
        }

    def _key_prefix(self, raw_key: str | None) -> str | None:
        if not raw_key:
            return f"{API_KEY_PREFIX}***"
        visible = min(18, len(raw_key))
        return f"{raw_key[:visible]}***"

    def _latest_power_amount_by_request_id(self, request_row_ids: list[int]) -> dict[int, str | None]:
        rows = (
            self.db.query(BillingRecord.id, BillingRecord.request_id, BillingRecord.power_amount)
            .filter(BillingRecord.request_id.in_(request_row_ids))
            .order_by(BillingRecord.id.desc())
            .all()
        )
        result: dict[int, str | None] = {}
        for row in rows:
            result.setdefault(
                row.request_id,
                str(row.power_amount) if row.power_amount is not None else None,
            )
        return result

    def _latest_billing_records_by_request_id(self, request_row_ids: list[int]) -> dict[int, BillingRecord]:
        if not request_row_ids:
            return {}
        rows = (
            self.db.query(BillingRecord)
            .filter(BillingRecord.request_id.in_(request_row_ids))
            .order_by(BillingRecord.id.desc())
            .all()
        )
        result: dict[int, BillingRecord] = {}
        for row in rows:
            result.setdefault(row.request_id, row)
        return result

    def _provider_models_by_request_id(self, request_row_ids: list[int]) -> dict[int, list[str]]:
        rows = (
            self.db.query(ProviderRequest.request_id, ProviderRequest.execution_model_code)
            .filter(ProviderRequest.request_id.in_(request_row_ids))
            .order_by(ProviderRequest.request_id.asc(), ProviderRequest.attempt_no.asc(), ProviderRequest.id.asc())
            .all()
        )
        result: dict[int, list[str]] = {}
        for row in rows:
            result.setdefault(row.request_id, []).append(row.execution_model_code)
        return result

    def _latest_billing_record(self, request_row_id: int) -> BillingRecord | None:
        return (
            self.db.query(BillingRecord)
            .filter(BillingRecord.request_id == request_row_id)
            .order_by(BillingRecord.id.desc())
            .first()
        )

    def _task_stats(self, *, user_id: int) -> dict[str, int]:
        rows = (
            self.db.query(Task.status, Task.request_id)
            .join(Request, Task.request_id == Request.id)
            .filter(Request.user_id == user_id)
            .all()
        )
        billing_map = self._latest_billing_records_by_request_id([row.request_id for row in rows])
        return {
            "active_count": sum(1 for row in rows if row.status in ACTIVE_TASK_STATUSES),
            "pending_billing_count": sum(
                1
                for row in rows
                if billing_map.get(row.request_id) is not None and billing_map[row.request_id].status == "pending"
            ),
            "completed_count": sum(1 for row in rows if row.status == "completed"),
            "failed_or_waived_count": sum(
                1
                for row in rows
                if row.status in {"failed", "cancelled", "canceled"}
                or (billing_map.get(row.request_id) is not None and billing_map[row.request_id].status == "waived")
            ),
        }

    def _route_type(self, route_group: str) -> str:
        route_group_lower = (route_group or "").lower()
        if "audio" in route_group_lower or "tts" in route_group_lower or "speech" in route_group_lower:
            return "audio"
        if "video" in route_group_lower or route_group_lower in {"veo", "kling", "wan"}:
            return "video"
        if any(keyword in route_group_lower for keyword in ("image", "seedream", "banana")):
            return "image"
        return "task"

    def _resolve_model(
        self,
        *,
        route_group: str,
        request_model: str | None,
        provider_rows: list[ProviderRequest] | list[str],
    ) -> str:
        if isinstance(request_model, str) and request_model:
            return request_model
        for provider_row in reversed(provider_rows):
            if isinstance(provider_row, str) and provider_row:
                return self._resolve_public_model_code(route_group=route_group, model_code=provider_row)
            if isinstance(provider_row, ProviderRequest) and provider_row.execution_model_code:
                return self._resolve_public_model_code(
                    route_group=route_group,
                    model_code=provider_row.execution_model_code,
                )
        return route_group

    def _resolve_public_model_code(self, *, route_group: str, model_code: str | None) -> str | None:
        return get_platform_config_snapshot().resolve_public_model_code(
            route_group=route_group,
            model_code=model_code,
        )

    def _request_model_from_body(self, request_body: dict[str, Any] | None) -> str | None:
        if not isinstance(request_body, dict):
            return None
        request_model = request_body.get("model")
        return request_model if isinstance(request_model, str) and request_model else None

    def _serialize_power_amount(self, billing_record: BillingRecord | None) -> str | None:
        if billing_record is None or billing_record.power_amount is None:
            return None
        return str(billing_record.power_amount)

    def _whitelist_headers(self, headers: dict[str, Any] | None) -> dict[str, Any]:
        if not headers:
            return {}
        result: dict[str, Any] = {}
        for key, value in headers.items():
            if key.lower() in self._HEADER_ALLOWLIST:
                result[key] = value
        return result

    def _serialize_provider_row(self, row: ProviderRequest) -> dict[str, Any]:
        return {
            "attempt_no": row.attempt_no,
            "provider_code": row.provider_code,
            "provider_account_id": row.provider_account_id,
            "provider_account_short_id": row.provider_account_short_id,
            "provider_account_owner_type": row.provider_account_owner_type,
            "model_code": row.execution_model_code,
            "provider_request_id": row.provider_request_id,
            "http_status_code": row.http_status_code,
            "status": row.status,
            "duration_ms": row.duration_ms,
            "fallback_reason": row.fallback_reason,
            "error_message": row.error_message,
        }

    def _serialize_task(self, task: Task) -> dict[str, Any]:
        return {
            "platform_task_id": task.platform_task_id,
            "provider_code": task.provider_code,
            "provider_account_id": task.provider_account_id,
            "provider_account_short_id": task.provider_account_short_id,
            "provider_account_owner_type": task.provider_account_owner_type,
            "provider_task_id": task.provider_task_id,
            "status": task.status,
            "created_at": self._serialize_datetime(task.created_at),
            "updated_at": self._serialize_datetime(task.updated_at),
            "finished_at": self._serialize_datetime(task.finished_at),
        }

    def _serialize_task_list_row(self, row: Any, *, billing_record: BillingRecord | None) -> dict[str, Any]:
        model = self._resolve_model(
            route_group=row.route_group,
            request_model=row.request_model,
            provider_rows=[row.public_model_code],
        )
        result_payload = row.result_payload if isinstance(row.result_payload, dict) else None
        return {
            "task_id": row.platform_task_id,
            "request_id": row.request_log_id,
            "model": model,
            "route_group": row.route_group,
            "route_type": self._route_type(row.route_group),
            "provider_code": row.provider_code,
            "provider_account_id": row.provider_account_id,
            "provider_account_short_id": row.provider_account_short_id,
            "provider_account_owner_type": row.provider_account_owner_type,
            "provider_task_id": row.provider_task_id,
            "task_status": row.task_status,
            "billing_status": billing_record.status if billing_record is not None else None,
            "result_available": bool(self._extract_result_urls(result_payload) or result_payload),
            "created_at": self._serialize_datetime(row.created_at),
            "updated_at": self._serialize_datetime(row.updated_at),
            "finished_at": self._serialize_datetime(row.finished_at),
        }

    def _build_response_summary(self, *, row: Request, task: Task | None) -> dict[str, Any] | None:
        if task is not None and task.result_payload is not None:
            return task.result_payload
        return row.response_body

    def _build_error_message(self, *, row: Request, provider_rows: list[ProviderRequest]) -> str | None:
        if row.status == "succeeded":
            return None
        if isinstance(row.response_body, dict):
            detail = row.response_body.get("detail")
            if isinstance(detail, str) and detail:
                return detail
            error = row.response_body.get("error")
            if isinstance(error, str) and error:
                return error
        for provider_row in reversed(provider_rows):
            if provider_row.error_message:
                return provider_row.error_message
        return None

    def _extract_result_urls(self, payload: Any) -> list[str]:
        if payload is None:
            return []
        result: list[str] = []
        seen: set[str] = set()

        def walk(value: Any) -> None:
            if len(result) >= 8:
                return
            if isinstance(value, str):
                if value.startswith(("http://", "https://")) and value not in seen:
                    seen.add(value)
                    result.append(value)
                return
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)
                return
            if isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)
        return result
