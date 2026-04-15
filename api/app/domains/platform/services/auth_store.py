from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domains.platform.entities.entities import AuthStoreEntry


class AuthStoreError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SqliteAuthStore:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def _session(self) -> Session:
        return self._session_factory()

    def _delete_expired_row(self, session: Session, row: AuthStoreEntry) -> None:
        session.delete(row)
        session.commit()

    def _lookup_active_row(self, session: Session, key: str) -> AuthStoreEntry | None:
        row = session.query(AuthStoreEntry).filter(AuthStoreEntry.store_key == key).first()
        if row is None:
            return None
        if _normalize_datetime(row.expires_at) <= _utc_now():
            self._delete_expired_row(session, row)
            return None
        return row

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        expires_at = _utc_now() + timedelta(seconds=max(int(ttl_seconds), 0))
        try:
            with self._session() as session:
                row = session.query(AuthStoreEntry).filter(AuthStoreEntry.store_key == key).first()
                if row is None:
                    row = AuthStoreEntry(store_key=key, store_value=value, expires_at=expires_at)
                else:
                    row.store_value = value
                    row.expires_at = expires_at
                session.add(row)
                session.commit()
            return True
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc

    def get(self, key: str) -> str | None:
        try:
            with self._session() as session:
                row = self._lookup_active_row(session, key)
                return None if row is None else row.store_value
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc

    def expire(self, key: str, ttl_seconds: int) -> bool:
        try:
            with self._session() as session:
                row = self._lookup_active_row(session, key)
                if row is None:
                    return False
                row.expires_at = _utc_now() + timedelta(seconds=max(int(ttl_seconds), 0))
                session.add(row)
                session.commit()
                return True
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc

    def delete(self, *keys: str) -> int:
        try:
            with self._session() as session:
                rows = session.query(AuthStoreEntry).filter(AuthStoreEntry.store_key.in_(keys)).all() if keys else []
                removed = len(rows)
                for row in rows:
                    session.delete(row)
                session.commit()
                return removed
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc

    def scan_iter(self, match: str | None = None):
        pattern = match or "*"
        try:
            with self._session() as session:
                rows = session.query(AuthStoreEntry).all()
                for row in rows:
                    if _normalize_datetime(row.expires_at) <= _utc_now():
                        session.delete(row)
                        continue
                    if fnmatch(row.store_key, pattern):
                        yield row.store_key
                session.commit()
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc

    def flushall(self) -> None:
        try:
            with self._session() as session:
                session.query(AuthStoreEntry).delete()
                session.commit()
        except Exception as exc:  # pragma: no cover - error path exercised via service layer
            raise AuthStoreError(str(exc)) from exc
