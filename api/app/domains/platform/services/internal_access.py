from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.api.auth import _read_bearer_token, _resolve_active_api_key
from app.db.session import SessionLocal
from app.domains.platform.services.auth_sessions import SESSION_TOKEN_PREFIX, SessionAuthService
from app.domains.platform.services.recharge import RechargeService
from app.domains.platform.services.system_api_keys import SystemApiKeyService


@dataclass
class InternalUserAccessContext:
    user_id: int
    auth_mode: str
    session_token: str | None = None


def _resolve_user_access_context(
    authorization: str,
    *,
    require_session: bool,
) -> InternalUserAccessContext:
    missing_detail = "missing_session_token" if require_session else "missing_user_auth"
    raw_token = _read_bearer_token(authorization, missing_detail=missing_detail)

    with SessionLocal() as db:
        if raw_token.startswith(SESSION_TOKEN_PREFIX):
            session_record = SessionAuthService(db).get_session_record(raw_token)
            if session_record is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")
            return InternalUserAccessContext(
                user_id=session_record.user_id,
                auth_mode="session",
                session_token=raw_token,
            )

        if require_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

        api_key = _resolve_active_api_key(db, raw_token)
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user_auth")

        api_key.last_used_at = datetime.now(timezone.utc)
        db.add(api_key)
        db.commit()
        return InternalUserAccessContext(
            user_id=api_key.user_id,
            auth_mode="api_key",
            session_token=None,
        )


def _get_session_me_from_authorization_sync(authorization: str) -> dict:
    raw_token = _read_bearer_token(authorization, missing_detail="missing_session_token")

    with SessionLocal() as db:
        auth_service = SessionAuthService(db)
        session_record = auth_service.get_session_record(raw_token)
        if session_record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")
        return auth_service.get_session_me(session_record=session_record)


async def get_session_me_from_authorization(authorization: str) -> dict:
    return await asyncio.to_thread(_get_session_me_from_authorization_sync, authorization)


def _get_system_default_api_key_for_session_authorization_sync(authorization: str) -> str:
    ctx = _resolve_user_access_context(authorization, require_session=True)

    with SessionLocal() as db:
        payload = SystemApiKeyService(db).get_system_default_key_response(user_id=ctx.user_id)

    api_key = str(payload.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="system_api_key_not_available")
    return api_key


async def get_system_default_api_key_for_session_authorization(authorization: str) -> str:
    return await asyncio.to_thread(_get_system_default_api_key_for_session_authorization_sync, authorization)


def _get_account_snapshot_from_authorization_sync(authorization: str) -> dict[str, str | int]:
    ctx = _resolve_user_access_context(authorization, require_session=False)

    with SessionLocal() as db:
        account = RechargeService(db).get_account(user_id=ctx.user_id)

    return {
        "user_id": ctx.user_id,
        "balance": str(account.balance),
        "status": account.status,
    }


async def get_account_snapshot_from_authorization(authorization: str) -> dict[str, str | int]:
    return await asyncio.to_thread(_get_account_snapshot_from_authorization_sync, authorization)
