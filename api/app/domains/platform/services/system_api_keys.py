from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.domains.platform.entities.entities import ApiKey, User

SYSTEM_DEFAULT_KEY_KIND = "system_default"
USER_CREATED_KEY_KIND = "user_created"
SYSTEM_DEFAULT_KEY_NAME = "System Default"


class SystemApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_system_default_key(self, *, user_id: int) -> ApiKey:
        self._get_user(user_id)
        row = self._get_system_default_key(user_id=user_id)
        if row is not None:
            return row

        raw_key = generate_api_key()
        row = ApiKey(
            user_id=user_id,
            key_name=SYSTEM_DEFAULT_KEY_NAME,
            key_kind=SYSTEM_DEFAULT_KEY_KIND,
            key_hash=hash_api_key(raw_key),
            key_plaintext=raw_key,
            status="active",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_system_default_key_response(self, *, user_id: int) -> dict[str, str | int | None]:
        row = self.ensure_system_default_key(user_id=user_id)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_api_key(row, include_plaintext=True)

    def reset_system_default_key(self, *, user_id: int) -> dict[str, str | int | None]:
        row = self.ensure_system_default_key(user_id=user_id)
        raw_key = generate_api_key()
        row.key_hash = hash_api_key(raw_key)
        row.key_plaintext = raw_key
        row.status = "active"
        row.last_used_at = None
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_api_key(row, include_plaintext=True)

    def assert_user_managed(self, row: ApiKey) -> None:
        if row.key_kind == SYSTEM_DEFAULT_KEY_KIND:
            raise HTTPException(status_code=403, detail="system_api_key_not_editable")

    def _get_system_default_key(self, *, user_id: int) -> ApiKey | None:
        return (
            self.db.query(ApiKey)
            .filter(
                ApiKey.user_id == user_id,
                ApiKey.key_kind == SYSTEM_DEFAULT_KEY_KIND,
            )
            .order_by(ApiKey.id.desc())
            .first()
        )

    def _get_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        return user

    def _serialize_api_key(
        self,
        row: ApiKey,
        *,
        include_plaintext: bool,
    ) -> dict[str, str | int | None]:
        return {
            "id": row.id,
            "key_name": row.key_name,
            "key_kind": row.key_kind,
            "key_prefix": self._key_prefix(row.key_plaintext),
            "api_key": row.key_plaintext if include_plaintext else None,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at is not None else None,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at is not None else None,
        }

    def _key_prefix(self, raw_key: str | None) -> str | None:
        if not raw_key:
            return None
        visible = min(18, len(raw_key))
        return f"{raw_key[:visible]}***"
