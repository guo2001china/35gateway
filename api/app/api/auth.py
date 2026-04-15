from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import verify_api_key
from app.domains.platform.entities.entities import ApiKey
from app.domains.platform.services.auth_sessions import SESSION_TOKEN_PREFIX, SessionAuthService


@dataclass
class ApiKeyContext:
    user_id: int
    api_key_id: int
    key_name: str


@dataclass
class UserAccessContext:
    user_id: int
    auth_mode: str
    api_key_id: int | None = None
    key_name: str | None = None
    session_id: str | None = None
    session_token: str | None = None


def require_admin_api_key(authorization: str | None = Header(default=None)) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="admin_not_configured")
    raw_key = _read_bearer_token(authorization, missing_detail="missing_admin_api_key")
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_admin_api_key")
    if not secrets.compare_digest(raw_key, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_admin_api_key")


def require_api_key(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKeyContext:
    raw_key = _read_bearer_token(authorization, missing_detail="missing_api_key")
    api_key = _resolve_active_api_key(db, raw_key)
    if api_key is not None:
        api_key.last_used_at = datetime.now(timezone.utc)
        db.add(api_key)
        db.commit()
        return ApiKeyContext(
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            key_name=api_key.key_name,
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")


def require_user_access(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserAccessContext:
    raw_token = _read_bearer_token(authorization, missing_detail="missing_user_auth")

    if raw_token.startswith(SESSION_TOKEN_PREFIX):
        session_record = SessionAuthService(db).get_session_record(raw_token)
        if session_record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")
        return UserAccessContext(
            user_id=session_record.user_id,
            auth_mode="session",
            session_id=session_record.session_id,
            session_token=raw_token,
        )

    api_key = _resolve_active_api_key(db, raw_token)
    if api_key is not None:
        api_key.last_used_at = datetime.now(timezone.utc)
        db.add(api_key)
        db.commit()
        return UserAccessContext(
            user_id=api_key.user_id,
            auth_mode="api_key",
            api_key_id=api_key.id,
            key_name=api_key.key_name,
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_user_auth")


def require_user_session(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserAccessContext:
    raw_token = _read_bearer_token(authorization, missing_detail="missing_session_token")
    session_record = SessionAuthService(db).get_session_record(raw_token)
    if session_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")
    return UserAccessContext(
        user_id=session_record.user_id,
        auth_mode="session",
        session_id=session_record.session_id,
        session_token=raw_token,
    )


def _read_bearer_token(authorization: str | None, *, missing_detail: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=missing_detail)
    raw_token = authorization.removeprefix("Bearer ").strip()
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=missing_detail)
    return raw_token


def _resolve_active_api_key(db: Session, raw_key: str) -> ApiKey | None:
    api_keys = db.query(ApiKey).filter(ApiKey.status == "active").all()
    for api_key in api_keys:
        if verify_api_key(raw_key, api_key.key_hash):
            return api_key
    return None
