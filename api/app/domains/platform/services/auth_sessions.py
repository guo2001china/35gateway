from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.domains.platform.entities.entities import User, UserAuthIdentity
from app.domains.platform.services.auth_store import AuthStoreError, SqliteAuthStore
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.google_oauth import GoogleOAuthError, GoogleOAuthService
from app.domains.platform.services.resend_email import ResendEmailError, ResendEmailService
from app.domains.platform.services.system_api_keys import SystemApiKeyService
from app.domains.platform.services.tencent_email import TencentEmailError, TencentEmailService
from app.domains.platform.services.tencent_sms import TencentSmsError, TencentSmsService
from app.domains.platform.services.yunpian_sms import YunpianSmsError, YunpianSmsService


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.IGNORECASE)
EMAIL_AUTH_PROVIDER = "email_otp"
GOOGLE_AUTH_PROVIDER = "google_oauth"
PASSWORD_AUTH_PROVIDER = "password_local"
PHONE_AUTH_PROVIDER = "phone_sms"
SESSION_TOKEN_PREFIX = "sess_api35_"
EMAIL_CODE_PREFIX = "auth:email-code:"
GOOGLE_STATE_PREFIX = "auth:google-state:"
PHONE_CODE_PREFIX = "auth:phone-code:"
SESSION_PREFIX = "auth:session:"


@dataclass
class SessionRecord:
    session_id: str
    user_id: int
    identity_id: int
    provider: str
    issued_at: str


@lru_cache
def get_auth_store() -> SqliteAuthStore:
    return SqliteAuthStore()


class SessionAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.auth_store = get_auth_store()

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def send_phone_code(self, *, phone: str) -> dict:
        normalized_phone = self.normalize_phone(phone)
        if self._is_test_phone(normalized_phone):
            return {
                "provider": PHONE_AUTH_PROVIDER,
                "phone": normalized_phone,
                "expires_in_seconds": settings.auth_phone_code_ttl_seconds,
                "debug_code": settings.auth_test_code,
            }

        code = f"{secrets.randbelow(1_000_000):06d}"
        payload = {
            "phone": normalized_phone,
            "code": code,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.auth_store.setex(
                self._phone_code_key(normalized_phone),
                settings.auth_phone_code_ttl_seconds,
                json.dumps(payload),
            )
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

        if settings.auth_sms_provider == "tencent":
            try:
                TencentSmsService().send_login_code(
                    phone=normalized_phone,
                    code=code,
                    ttl_seconds=settings.auth_phone_code_ttl_seconds,
                )
            except TencentSmsError as exc:
                self._delete_phone_code(normalized_phone)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc
        elif settings.auth_sms_provider == "yunpian":
            try:
                YunpianSmsService().send_login_code(
                    phone=normalized_phone,
                    code=code,
                    ttl_seconds=settings.auth_phone_code_ttl_seconds,
                )
            except YunpianSmsError as exc:
                self._delete_phone_code(normalized_phone)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc

        return {
            "provider": PHONE_AUTH_PROVIDER,
            "phone": normalized_phone,
            "expires_in_seconds": settings.auth_phone_code_ttl_seconds,
            "debug_code": code if settings.app_env != "prod" else None,
        }

    def send_email_code(self, *, email: str) -> dict:
        normalized_email = self.normalize_email(email)
        if self._is_test_email(normalized_email):
            return {
                "provider": EMAIL_AUTH_PROVIDER,
                "email": normalized_email,
                "expires_in_seconds": settings.auth_email_code_ttl_seconds,
                "debug_code": settings.auth_test_email_code,
            }

        code = f"{secrets.randbelow(1_000_000):06d}"
        payload = {
            "email": normalized_email,
            "code": code,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.auth_store.setex(
                self._email_code_key(normalized_email),
                settings.auth_email_code_ttl_seconds,
                json.dumps(payload),
            )
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

        if settings.auth_email_provider == "resend":
            try:
                ResendEmailService().send_login_code(
                    email=normalized_email,
                    code=code,
                    ttl_seconds=settings.auth_email_code_ttl_seconds,
                )
            except ResendEmailError as exc:
                self._delete_email_code(normalized_email)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc
        elif settings.auth_email_provider == "tencent":
            try:
                TencentEmailService().send_login_code(
                    email=normalized_email,
                    code=code,
                    ttl_seconds=settings.auth_email_code_ttl_seconds,
                )
            except TencentEmailError as exc:
                self._delete_email_code(normalized_email)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc

        return {
            "provider": EMAIL_AUTH_PROVIDER,
            "email": normalized_email,
            "expires_in_seconds": settings.auth_email_code_ttl_seconds,
            "debug_code": code if settings.app_env != "prod" else None,
        }

    def get_google_login_url(self, *, next_path: str, redirect_uri: str) -> str:
        normalized_next = self.normalize_next_path(next_path)
        oauth = GoogleOAuthService()
        if not oauth.is_configured():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="google_oauth_not_configured")

        state = secrets.token_urlsafe(24)
        self._store_google_state(state=state, next_path=normalized_next)
        return oauth.build_authorization_url(redirect_uri=redirect_uri, state=state)

    def login_with_phone(self, *, phone: str, code: str, growth_context: dict[str, Any] | None = None) -> dict:
        normalized_phone = self.normalize_phone(phone)
        normalized_code = code.strip()
        if not normalized_code:
            raise HTTPException(status_code=422, detail="invalid_phone_code")

        now = datetime.now(timezone.utc)
        if not self._matches_test_code(normalized_phone, normalized_code):
            payload = self._load_phone_code(normalized_phone)
            stored_code = str(payload.get("code") or "")
            if not stored_code or not secrets.compare_digest(stored_code, normalized_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_phone_code")

        user, identity = self._get_or_create_phone_user(normalized_phone, now)

        session_token = self._new_session_token()
        session_record = SessionRecord(
            session_id=secrets.token_urlsafe(12),
            user_id=user.id,
            identity_id=identity.id,
            provider=identity.provider,
            issued_at=now.isoformat(),
        )
        BusinessTrackingService(self.db).sync_growth_context(
            user_id=user.id,
            growth_context=growth_context,
        )
        self.db.commit()
        self._store_session(session_token, session_record)
        self._delete_phone_code(normalized_phone)

        return {
            "provider": identity.provider,
            "session_token": session_token,
            "expires_in_seconds": settings.auth_session_ttl_seconds,
            "user": self._serialize_user(user, identity),
        }

    def login_with_email(self, *, email: str, code: str, growth_context: dict[str, Any] | None = None) -> dict:
        normalized_email = self.normalize_email(email)
        normalized_code = code.strip()
        if not normalized_code:
            raise HTTPException(status_code=422, detail="invalid_email_code")

        now = datetime.now(timezone.utc)
        if not self._matches_test_email_code(normalized_email, normalized_code):
            payload = self._load_email_code(normalized_email)
            stored_code = str(payload.get("code") or "")
            if not stored_code or not secrets.compare_digest(stored_code, normalized_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_email_code")

        user, identity = self._get_or_create_email_user(normalized_email, now)

        session_token = self._new_session_token()
        session_record = SessionRecord(
            session_id=secrets.token_urlsafe(12),
            user_id=user.id,
            identity_id=identity.id,
            provider=identity.provider,
            issued_at=now.isoformat(),
        )
        BusinessTrackingService(self.db).sync_growth_context(
            user_id=user.id,
            growth_context=growth_context,
        )
        self.db.commit()
        self._store_session(session_token, session_record)
        self._delete_email_code(normalized_email)

        return {
            "provider": identity.provider,
            "session_token": session_token,
            "expires_in_seconds": settings.auth_session_ttl_seconds,
            "user": self._serialize_user(user, identity),
        }

    def login_with_password(
        self,
        *,
        email: str,
        password: str,
        growth_context: dict[str, Any] | None = None,
    ) -> dict:
        normalized_email = self.normalize_email(email)
        normalized_password = self.validate_password(password)

        identity = (
            self.db.query(UserAuthIdentity)
            .filter(
                UserAuthIdentity.provider == PASSWORD_AUTH_PROVIDER,
                UserAuthIdentity.provider_user_id == normalized_email,
            )
            .first()
        )
        if identity is None or not verify_password(normalized_password, identity.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_email_or_password")

        user = self.db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")

        now = datetime.now(timezone.utc)
        identity.email = normalized_email
        identity.last_login_at = now
        self.db.add(identity)
        self.db.flush()
        SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)

        session_token = self._new_session_token()
        session_record = SessionRecord(
            session_id=secrets.token_urlsafe(12),
            user_id=user.id,
            identity_id=identity.id,
            provider=identity.provider,
            issued_at=now.isoformat(),
        )
        BusinessTrackingService(self.db).sync_growth_context(
            user_id=user.id,
            growth_context=growth_context,
        )
        self.db.commit()
        self._store_session(session_token, session_record)

        return {
            "provider": identity.provider,
            "session_token": session_token,
            "expires_in_seconds": settings.auth_session_ttl_seconds,
            "user": self._serialize_user(user, identity),
        }

    def register_with_password(
        self,
        *,
        email: str,
        code: str,
        password: str,
        growth_context: dict[str, Any] | None = None,
    ) -> dict:
        normalized_email = self.normalize_email(email)
        normalized_code = code.strip()
        normalized_password = self.validate_password(password)
        if not normalized_code:
            raise HTTPException(status_code=422, detail="invalid_email_code")

        now = datetime.now(timezone.utc)
        if not self._matches_test_email_code(normalized_email, normalized_code):
            payload = self._load_email_code(normalized_email)
            stored_code = str(payload.get("code") or "")
            if not stored_code or not secrets.compare_digest(stored_code, normalized_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_email_code")

        user, _ = self._get_or_create_email_user(normalized_email, now)
        identity = (
            self.db.query(UserAuthIdentity)
            .filter(
                UserAuthIdentity.provider == PASSWORD_AUTH_PROVIDER,
                UserAuthIdentity.provider_user_id == normalized_email,
            )
            .first()
        )
        if identity is None:
            identity = UserAuthIdentity(
                user_id=user.id,
                provider=PASSWORD_AUTH_PROVIDER,
                provider_user_id=normalized_email,
                email=normalized_email,
                password_hash=hash_password(normalized_password),
                password_updated_at=now,
                profile={"email": normalized_email},
                last_login_at=now,
            )
            self.db.add(identity)
            self.db.flush()
        else:
            identity.email = normalized_email
            identity.password_hash = hash_password(normalized_password)
            identity.password_updated_at = now
            identity.last_login_at = now
            self.db.add(identity)
            self.db.flush()

        session_token = self._new_session_token()
        session_record = SessionRecord(
            session_id=secrets.token_urlsafe(12),
            user_id=user.id,
            identity_id=identity.id,
            provider=identity.provider,
            issued_at=now.isoformat(),
        )
        tracking = BusinessTrackingService(self.db)
        tracking.sync_growth_context(
            user_id=user.id,
            growth_context=growth_context,
        )
        tracking.record_event(
            user_id=user.id,
            event_name="signup_completed",
            currency=None,
            context_payload={"provider": identity.provider},
            occurred_at=now,
        )
        self.db.commit()
        self._store_session(session_token, session_record)
        self._delete_email_code(normalized_email)

        return {
            "provider": identity.provider,
            "session_token": session_token,
            "expires_in_seconds": settings.auth_session_ttl_seconds,
            "user": self._serialize_user(user, identity),
        }

    def login_with_google(self, *, code: str, state: str, redirect_uri: str) -> dict:
        normalized_state = state.strip()
        normalized_code = code.strip()
        if not normalized_state:
            raise HTTPException(status_code=422, detail="invalid_google_state")
        if not normalized_code:
            raise HTTPException(status_code=422, detail="invalid_google_code")

        next_path = self._consume_google_state(normalized_state)
        oauth = GoogleOAuthService()
        try:
            token_data = oauth.exchange_code(code=normalized_code, redirect_uri=redirect_uri)
            profile = oauth.fetch_userinfo(access_token=str(token_data["access_token"]))
        except GoogleOAuthError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        if not bool(profile.get("email_verified")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="google_email_not_verified")

        now = datetime.now(timezone.utc)
        user, identity = self._get_or_create_google_user(profile=profile, now=now)

        session_token = self._new_session_token()
        session_record = SessionRecord(
            session_id=secrets.token_urlsafe(12),
            user_id=user.id,
            identity_id=identity.id,
            provider=identity.provider,
            issued_at=now.isoformat(),
        )
        self.db.commit()
        self._store_session(session_token, session_record)

        return {
            "provider": identity.provider,
            "session_token": session_token,
            "expires_in_seconds": settings.auth_session_ttl_seconds,
            "user": self._serialize_user(user, identity),
            "next_path": next_path,
        }

    def _get_or_create_phone_user(self, phone: str, now: datetime) -> tuple[User, UserAuthIdentity]:
        identity = (
            self.db.query(UserAuthIdentity)
            .filter(
                UserAuthIdentity.provider == PHONE_AUTH_PROVIDER,
                UserAuthIdentity.provider_user_id == phone,
            )
            .first()
        )

        if identity is None:
            user = User(
                user_no=self._new_user_no(),
                name=self._default_user_name(phone),
                balance=Decimal("0"),
                status="active",
            )
            self.db.add(user)
            self.db.flush()

            identity = UserAuthIdentity(
                user_id=user.id,
                provider=PHONE_AUTH_PROVIDER,
                provider_user_id=phone,
                phone=phone,
                profile={"phone": phone},
                last_login_at=now,
            )
            self.db.add(identity)
            self.db.flush()
            SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
            return user, identity

        user = self.db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        identity.phone = phone
        identity.last_login_at = now
        self.db.add(identity)
        self.db.flush()
        SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
        return user, identity

    def _get_or_create_email_user(self, email: str, now: datetime) -> tuple[User, UserAuthIdentity]:
        identity = (
            self.db.query(UserAuthIdentity)
            .filter(
                UserAuthIdentity.provider == EMAIL_AUTH_PROVIDER,
                UserAuthIdentity.provider_user_id == email,
            )
            .first()
        )

        if identity is None:
            user = self._find_user_by_email(email)
            if user is None:
                user = User(
                    user_no=self._new_user_no(),
                    name=self._default_email_user_name(email),
                    balance=Decimal("0"),
                    status="active",
                )
                self.db.add(user)
                self.db.flush()

            identity = UserAuthIdentity(
                user_id=user.id,
                provider=EMAIL_AUTH_PROVIDER,
                provider_user_id=email,
                email=email,
                profile={"email": email},
                last_login_at=now,
            )
            self.db.add(identity)
            self.db.flush()
            SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
            return user, identity

        user = self.db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        identity.email = email
        identity.last_login_at = now
        self.db.add(identity)
        self.db.flush()
        SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
        return user, identity

    def _get_or_create_google_user(self, *, profile: dict, now: datetime) -> tuple[User, UserAuthIdentity]:
        subject = str(profile.get("sub") or "").strip()
        email = self.normalize_email(str(profile.get("email") or ""))
        name = str(profile.get("name") or "").strip()
        picture = str(profile.get("picture") or "").strip()

        identity = (
            self.db.query(UserAuthIdentity)
            .filter(
                UserAuthIdentity.provider == GOOGLE_AUTH_PROVIDER,
                UserAuthIdentity.provider_user_id == subject,
            )
            .first()
        )

        if identity is None:
            user = self._find_user_by_email(email)
            if user is None:
                user = User(
                    user_no=self._new_user_no(),
                    name=name or self._default_email_user_name(email),
                    balance=Decimal("0"),
                    status="active",
                )
                self.db.add(user)
                self.db.flush()

            identity = UserAuthIdentity(
                user_id=user.id,
                provider=GOOGLE_AUTH_PROVIDER,
                provider_user_id=subject,
                email=email,
                profile={"email": email, "name": name, "picture": picture, "google": profile},
                last_login_at=now,
            )
            self.db.add(identity)
            self.db.flush()
            if name:
                user.name = name
                self.db.add(user)
                self.db.flush()
            SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
            return user, identity

        user = self.db.get(User, identity.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        if name:
            user.name = name
            self.db.add(user)
        identity.email = email
        identity.profile = {"email": email, "name": name, "picture": picture, "google": profile}
        identity.last_login_at = now
        self.db.add(identity)
        self.db.flush()
        SystemApiKeyService(self.db).ensure_system_default_key(user_id=user.id)
        return user, identity

    def get_session_record(self, token: str) -> SessionRecord | None:
        if not token.startswith(SESSION_TOKEN_PREFIX):
            return None
        try:
            raw_payload = self.auth_store.get(self._session_key(token))
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

        if not raw_payload:
            return None

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return None

        try:
            self.auth_store.expire(self._session_key(token), settings.auth_session_ttl_seconds)
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

        return SessionRecord(
            session_id=str(payload.get("session_id") or ""),
            user_id=int(payload["user_id"]),
            identity_id=int(payload["identity_id"]),
            provider=str(payload.get("provider") or ""),
            issued_at=str(payload.get("issued_at") or ""),
        )

    def get_session_me(self, *, session_record: SessionRecord) -> dict:
        user = self.db.get(User, session_record.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        identity = self.db.get(UserAuthIdentity, session_record.identity_id)
        if identity is None:
            raise HTTPException(status_code=404, detail="auth_identity_not_found")
        return {
            "auth_mode": "session",
            "provider": identity.provider,
            "user": self._serialize_user(user, identity),
            "issued_at": session_record.issued_at,
            "last_login_at": self._serialize_datetime(identity.last_login_at),
        }

    def revoke_session(self, *, token: str) -> bool:
        try:
            return bool(self.auth_store.delete(self._session_key(token)))
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

    def _load_phone_code(self, phone: str) -> dict:
        try:
            raw_payload = self.auth_store.get(self._phone_code_key(phone))
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc
        if not raw_payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="phone_code_expired")
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_phone_code")
        return payload

    def _load_email_code(self, email: str) -> dict:
        try:
            raw_payload = self.auth_store.get(self._email_code_key(email))
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc
        if not raw_payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="email_code_expired")
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_email_code")
        return payload

    def _store_google_state(self, *, state: str, next_path: str) -> None:
        payload = {
            "next_path": next_path,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.auth_store.setex(
                self._google_state_key(state),
                settings.auth_google_state_ttl_seconds,
                json.dumps(payload),
            )
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

    def _consume_google_state(self, state: str) -> str:
        try:
            raw_payload = self.auth_store.get(self._google_state_key(state))
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc
        if not raw_payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="google_state_expired")
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_google_state")
        try:
            self.auth_store.delete(self._google_state_key(state))
        except AuthStoreError:
            pass
        return self.normalize_next_path(str(payload.get("next_path") or "/"))

    def _store_session(self, token: str, session_record: SessionRecord) -> None:
        payload = {
            "session_id": session_record.session_id,
            "user_id": session_record.user_id,
            "identity_id": session_record.identity_id,
            "provider": session_record.provider,
            "issued_at": session_record.issued_at,
        }
        try:
            self.auth_store.setex(
                self._session_key(token),
                settings.auth_session_ttl_seconds,
                json.dumps(payload),
            )
        except AuthStoreError as exc:
            raise self._auth_store_error() from exc

    def _delete_phone_code(self, phone: str) -> None:
        try:
            self.auth_store.delete(self._phone_code_key(phone))
        except AuthStoreError:
            return

    def _delete_email_code(self, email: str) -> None:
        try:
            self.auth_store.delete(self._email_code_key(email))
        except AuthStoreError:
            return

    def _find_user_by_email(self, email: str) -> User | None:
        identity = (
            self.db.query(UserAuthIdentity)
            .filter(UserAuthIdentity.email == email)
            .order_by(UserAuthIdentity.id.asc())
            .first()
        )
        if identity is None:
            return None
        return self.db.get(User, identity.user_id)

    def _serialize_user(self, user: User, identity: UserAuthIdentity | None) -> dict:
        return {
            "user_id": user.id,
            "user_no": user.user_no,
            "name": user.name,
            "status": user.status,
            "phone": identity.phone if identity is not None else None,
            "email": identity.email if identity is not None else None,
        }

    def _default_user_name(self, phone: str) -> str:
        suffix = phone[-4:] if len(phone) >= 4 else phone
        return f"用户{suffix}"

    def _default_email_user_name(self, email: str) -> str:
        local_part = email.split("@", 1)[0]
        normalized = (local_part or "用户").strip()[:24]
        return normalized or "用户"

    def _is_test_phone(self, phone: str) -> bool:
        return settings.app_env != "prod" and bool(settings.auth_test_phone) and phone == settings.auth_test_phone

    def _matches_test_code(self, phone: str, code: str) -> bool:
        return self._is_test_phone(phone) and bool(settings.auth_test_code) and code == settings.auth_test_code

    def _is_test_email(self, email: str) -> bool:
        return settings.app_env != "prod" and bool(settings.auth_test_email) and email == settings.auth_test_email

    def _matches_test_email_code(self, email: str, code: str) -> bool:
        return (
            self._is_test_email(email)
            and bool(settings.auth_test_email_code)
            and code == settings.auth_test_email_code
        )

    def _new_user_no(self) -> str:
        return f"u_{secrets.token_hex(5)}"

    def _new_session_token(self) -> str:
        return f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(24)}"

    def _email_code_key(self, email: str) -> str:
        return f"{EMAIL_CODE_PREFIX}{email}"

    def _google_state_key(self, state: str) -> str:
        return f"{GOOGLE_STATE_PREFIX}{state}"

    def _phone_code_key(self, phone: str) -> str:
        return f"{PHONE_CODE_PREFIX}{phone}"

    def _session_key(self, token: str) -> str:
        return f"{SESSION_PREFIX}{token}"

    def _auth_store_error(self) -> HTTPException:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="auth_store_unavailable")

    @staticmethod
    def normalize_phone(phone: str) -> str:
        normalized = "".join(char for char in phone.strip() if char.isdigit() or char == "+")
        if not normalized:
            raise HTTPException(status_code=422, detail="invalid_phone")
        if normalized.startswith("+"):
            if normalized.count("+") > 1 or len(normalized) < 8:
                raise HTTPException(status_code=422, detail="invalid_phone")
            return normalized

        digits = "".join(char for char in normalized if char.isdigit())
        if len(digits) < 6 or len(digits) > 20:
            raise HTTPException(status_code=422, detail="invalid_phone")
        return digits

    @staticmethod
    def normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if len(normalized) < 6 or len(normalized) > 254:
            raise HTTPException(status_code=422, detail="invalid_email")
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise HTTPException(status_code=422, detail="invalid_email")
        return normalized

    @staticmethod
    def validate_password(password: str) -> str:
        if len(password) < 8 or len(password) > 128 or not password.strip():
            raise HTTPException(status_code=422, detail="invalid_password")
        return password

    @staticmethod
    def normalize_next_path(raw_next: str | None) -> str:
        normalized = (raw_next or "").strip()
        if not normalized.startswith("/"):
            return "/"
        if normalized in {"/login", "/console/login"}:
            return "/"
        if normalized.startswith("/login?") or normalized.startswith("/console/login?"):
            return "/"
        return normalized

    @staticmethod
    def encode_console_hash(*, session_token: str | None = None, next_path: str | None = None, auth_error: str | None = None) -> str:
        parts: list[str] = []
        if session_token:
            parts.append(f"session_token={quote(session_token, safe='')}")
        if next_path:
            parts.append(f"next={quote(next_path, safe='/')}")
        if auth_error:
            parts.append(f"auth_error={quote(auth_error, safe='')}")
        return "&".join(parts)
