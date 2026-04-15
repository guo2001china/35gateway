from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import secrets
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.provider_catalog import get_provider, list_providers
from app.core.provider_catalog.types import ProviderConfig
from app.domains.platform.entities.entities import PlatformModelProviderBinding, ProviderAccount, User

OWNER_TYPE_PLATFORM = "platform"
OWNER_TYPE_USER = "user"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_DELETED = "deleted"

VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_VERIFIED = "verified"
VERIFICATION_FAILED = "failed"

BALANCE_UNSUPPORTED = "unsupported"
BALANCE_OK = "ok"
BALANCE_FAILED = "failed"
_PROVIDER_SHORT_ALIASES: dict[str, str] = {
    "openai_official": "oa",
    "openrouter": "or",
    "google_official": "go",
    "google_openai_compat": "go",
    "google_veo3": "go",
    "fal_nano_banana": "fa",
    "fal_veo3": "fa",
    "fal_veo31": "fa",
    "qwen_official": "qw",
    "wan_official": "wa",
    "minimax_official": "mm",
    "kling_official": "kl",
    "grsai_nano_banana": "gr",
    "volcengine_seedream": "vs",
    "yunwu_openai": "yw",
    "ksyun_openai": "ks",
    "deepseek_official": "ds",
    "cloudflare_workers_ai": "cf",
    "35m": "35",
    "vidu_official": "vi",
}

_DEFAULT_AUTH_FIELDS = [
    {
        "field_name": "api_key",
        "label": "API Key",
        "required": True,
        "secret": True,
    }
]

_PROVIDER_AUTH_FIELDS: dict[str, list[dict[str, Any]]] = {
    "kling_official": [
        {
            "field_name": "api_key",
            "label": "API Key",
            "required": False,
            "secret": True,
        },
        {
            "field_name": "access_key",
            "label": "Access Key",
            "required": False,
            "secret": True,
        },
        {
            "field_name": "secret_key",
            "label": "Secret Key",
            "required": False,
            "secret": True,
        },
    ],
}

_BALANCE_SUPPORTED_PROVIDER_CODES = {"openrouter", "vidu_official"}
_EXCLUDED_PROVIDER_OPTION_CODES: set[str] = set()
_ENV_SYNC_NOTES_PREFIX = "[env-sync]"


def _format_provider_name(provider_code: str) -> str:
    try:
        return get_provider(provider_code).provider_name
    except KeyError:
        label = provider_code.replace("_", " ").replace("-", " ").strip()
        return " ".join(part.capitalize() for part in label.split()) or provider_code


def _provider_auth_fields(provider_code: str) -> list[dict[str, Any]]:
    return [dict(item) for item in _PROVIDER_AUTH_FIELDS.get(provider_code, _DEFAULT_AUTH_FIELDS)]


def _provider_supports_balance_sync(provider_code: str) -> bool:
    return provider_code in _BALANCE_SUPPORTED_PROVIDER_CODES


def _normalize_base_url(base_url: str | None, fallback: str | None = None) -> str:
    return str(base_url or fallback or "").strip().rstrip("/")


def _join_url(base_url: str, path: str) -> str:
    normalized = f"{base_url}/" if not base_url.endswith("/") else base_url
    return urljoin(normalized, path.lstrip("/"))


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _openai_probe_paths(provider_code: str, base_url: str) -> list[str]:
    normalized = base_url.rstrip("/")
    if provider_code in {"openai_official", "35m"} and not normalized.endswith("/v1"):
        return ["/v1/models", "/models"]
    return ["/models"]


class ProviderAccountService:
    def __init__(self, db: Session):
        self.db = db

    def list_provider_options(self) -> list[dict[str, Any]]:
        bound_provider_codes = {
            str(code)
            for (code,) in self.db.query(PlatformModelProviderBinding.provider_code).distinct().all()
            if code
        }
        catalog_provider_codes = {provider.provider_code for provider in list_providers()}
        provider_codes = sorted(bound_provider_codes | catalog_provider_codes)
        return [
            {
                "provider_code": provider_code,
                "provider_name": _format_provider_name(provider_code),
                "supports_balance_sync": _provider_supports_balance_sync(provider_code),
                "auth_fields": _provider_auth_fields(provider_code),
            }
            for provider_code in provider_codes
            if provider_code not in _EXCLUDED_PROVIDER_OPTION_CODES
        ]

    def list_user_accounts(self, *, user_id: int) -> list[dict[str, Any]]:
        self._get_user(user_id)
        rows = (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.owner_type == OWNER_TYPE_USER,
                ProviderAccount.user_id == user_id,
                ProviderAccount.status != STATUS_DELETED,
            )
            .order_by(ProviderAccount.priority.asc(), ProviderAccount.id.asc())
            .all()
        )
        return [self._serialize_account(row) for row in rows]

    def list_platform_accounts(
        self,
        *,
        provider_code: str | None = None,
        status: str | None = None,
        routing_enabled_only: bool = False,
        only_abnormal: bool = False,
    ) -> list[dict[str, Any]]:
        query = self.db.query(ProviderAccount).filter(
            ProviderAccount.owner_type == OWNER_TYPE_PLATFORM,
            ProviderAccount.status != STATUS_DELETED,
        )
        if provider_code and provider_code != "all":
            query = query.filter(ProviderAccount.provider_code == provider_code)
        if status and status != "all":
            query = query.filter(ProviderAccount.status == status)
        if routing_enabled_only:
            query = query.filter(ProviderAccount.routing_enabled.is_(True))

        rows = query.order_by(ProviderAccount.priority.asc(), ProviderAccount.id.asc()).all()
        serialized = [self._serialize_account(row) for row in rows]
        if only_abnormal:
            serialized = [
                item
                for item in serialized
                if item["verification_status"] == VERIFICATION_FAILED
                or item["balance_status"] == BALANCE_FAILED
            ]
        return serialized

    def create_user_account(self, *, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_user(user_id)
        return self._create_account(owner_type=OWNER_TYPE_USER, user_id=user_id, payload=payload)

    def update_user_account(self, *, user_id: int, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_USER, user_id=user_id, account_id=account_id)
        return self._update_account(row=row, payload=payload, allow_routing_enabled=False)

    def delete_user_account(self, *, user_id: int, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_USER, user_id=user_id, account_id=account_id)
        return self._delete_account(row=row)

    def verify_user_account(self, *, user_id: int, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_USER, user_id=user_id, account_id=account_id)
        return self._verify_account(row=row)

    def sync_balance_user_account(self, *, user_id: int, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_USER, user_id=user_id, account_id=account_id)
        return self._sync_balance(row=row)

    def create_platform_account(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return self._create_account(owner_type=OWNER_TYPE_PLATFORM, user_id=None, payload=payload)

    def update_platform_account(self, *, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_PLATFORM, user_id=None, account_id=account_id)
        return self._update_account(row=row, payload=payload, allow_routing_enabled=True)

    def delete_platform_account(self, *, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_PLATFORM, user_id=None, account_id=account_id)
        return self._delete_account(row=row)

    def verify_platform_account(self, *, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_PLATFORM, user_id=None, account_id=account_id)
        return self._verify_account(row=row)

    def sync_balance_platform_account(self, *, account_id: int) -> dict[str, Any]:
        row = self._get_owned_account(owner_type=OWNER_TYPE_PLATFORM, user_id=None, account_id=account_id)
        return self._sync_balance(row=row)

    def sync_platform_accounts_from_env(self) -> list[dict[str, Any]]:
        synced_rows: list[dict[str, Any]] = []
        for index, provider in enumerate(self._list_env_backed_provider_configs(), start=1):
            existing = self._find_env_synced_platform_account(provider.provider_code)
            credential_payload = self._normalize_credential_payload(provider.auth_config)
            payload: dict[str, Any] = {
                "display_name": f"{provider.provider_name} 平台账号",
                "base_url_override": _normalize_optional_text(provider.base_url),
                "credential_payload": credential_payload,
                "notes": f"{_ENV_SYNC_NOTES_PREFIX} 来自环境变量",
            }
            if existing is None:
                payload.update(
                    {
                        "provider_code": provider.provider_code,
                        "status": STATUS_ACTIVE,
                        "routing_enabled": True,
                        "priority": index * 10,
                    }
                )
                synced_rows.append(self.create_platform_account(payload=payload))
                continue

            synced_rows.append(
                self.update_platform_account(
                    account_id=existing.id,
                    payload=payload,
                )
            )
        return synced_rows

    def _create_account(self, *, owner_type: str, user_id: int | None, payload: dict[str, Any]) -> dict[str, Any]:
        provider_code = self._validate_provider_code(str(payload.get("provider_code") or ""))
        credential_payload = self._normalize_credential_payload(payload.get("credential_payload") or {})
        self._validate_credentials(provider_code=provider_code, credential_payload=credential_payload)
        row = ProviderAccount(
            short_id=self._generate_short_id(provider_code),
            owner_type=owner_type,
            user_id=user_id,
            provider_code=provider_code,
            display_name=str(payload.get("display_name") or "").strip(),
            status=str(payload.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE,
            routing_enabled=bool(payload.get("routing_enabled", True)),
            priority=int(payload.get("priority") or 100),
            base_url_override=self._normalize_optional_text(payload.get("base_url_override")),
            credential_payload=credential_payload,
            notes=self._normalize_optional_text(payload.get("notes")),
            balance_status=BALANCE_UNSUPPORTED,
        )
        if owner_type == OWNER_TYPE_USER:
            row.routing_enabled = True
        self._validate_display_name(row.display_name)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_account(row)

    def _update_account(
        self,
        *,
        row: ProviderAccount,
        payload: dict[str, Any],
        allow_routing_enabled: bool,
    ) -> dict[str, Any]:
        if not payload:
            raise HTTPException(status_code=422, detail="empty_update_payload")

        if "display_name" in payload and payload.get("display_name") is not None:
            row.display_name = str(payload.get("display_name") or "").strip()
            self._validate_display_name(row.display_name)
        if "base_url_override" in payload:
            row.base_url_override = self._normalize_optional_text(payload.get("base_url_override"))
        if "credential_payload" in payload and payload.get("credential_payload") is not None:
            credential_payload = self._normalize_credential_payload(payload.get("credential_payload") or {})
            self._validate_credentials(provider_code=row.provider_code, credential_payload=credential_payload)
            row.credential_payload = credential_payload
            row.verification_status = VERIFICATION_UNVERIFIED
            row.last_verification_error = None
        if "status" in payload and payload.get("status") is not None:
            row.status = str(payload.get("status") or "").strip() or row.status
        if allow_routing_enabled and "routing_enabled" in payload and payload.get("routing_enabled") is not None:
            row.routing_enabled = bool(payload.get("routing_enabled"))
        if "priority" in payload and payload.get("priority") is not None:
            row.priority = int(payload.get("priority"))
        if "notes" in payload:
            row.notes = self._normalize_optional_text(payload.get("notes"))

        if row.owner_type == OWNER_TYPE_USER:
            row.routing_enabled = True

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_account(row)

    def _delete_account(self, *, row: ProviderAccount) -> dict[str, Any]:
        row.status = STATUS_DELETED
        row.routing_enabled = False
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_account(row)

    def _verify_account(self, *, row: ProviderAccount) -> dict[str, Any]:
        provider_code = row.provider_code
        credentials = dict(row.credential_payload or {})
        self._validate_credentials(provider_code=provider_code, credential_payload=credentials)
        now = datetime.now(timezone.utc)

        try:
            self._probe_provider_connection(
                provider_code=provider_code,
                credentials=credentials,
                base_url_override=row.base_url_override,
            )
        except HTTPException as exc:
            row.verification_status = VERIFICATION_FAILED
            row.last_verified_at = now
            row.last_verification_error = str(exc.detail)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            raise
        except Exception as exc:  # pragma: no cover - defensive for network probes
            row.verification_status = VERIFICATION_FAILED
            row.last_verified_at = now
            row.last_verification_error = str(exc)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            raise HTTPException(status_code=503, detail=f"provider_account_verify_failed:{exc}") from exc

        row.verification_status = VERIFICATION_VERIFIED
        row.last_verified_at = now
        row.last_verification_error = None
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_account(row)

    def _sync_balance(self, *, row: ProviderAccount) -> dict[str, Any]:
        if not _provider_supports_balance_sync(row.provider_code):
            raise HTTPException(status_code=422, detail="provider_account_balance_not_supported")

        try:
            balance_amount, currency = self._fetch_balance(
                provider_code=row.provider_code,
                credentials=dict(row.credential_payload or {}),
                base_url_override=row.base_url_override,
            )
        except HTTPException:
            row.balance_status = BALANCE_FAILED
            row.balance_updated_at = datetime.now(timezone.utc)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            row.balance_status = BALANCE_FAILED
            row.balance_updated_at = datetime.now(timezone.utc)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            raise HTTPException(status_code=503, detail=f"provider_account_balance_sync_failed:{exc}") from exc

        row.balance_status = BALANCE_OK
        row.balance_amount = balance_amount
        row.balance_currency = currency
        row.balance_updated_at = datetime.now(timezone.utc)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize_account(row)

    def _serialize_account(
        self,
        row: ProviderAccount,
    ) -> dict[str, Any]:
        return {
            "id": row.id,
            "short_id": row.short_id,
            "owner_type": row.owner_type,
            "user_id": row.user_id,
            "provider_code": row.provider_code,
            "provider_name": _format_provider_name(row.provider_code),
            "display_name": row.display_name,
            "status": row.status,
            "routing_enabled": bool(row.routing_enabled),
            "priority": int(row.priority),
            "base_url_override": row.base_url_override,
            "verification_status": row.verification_status,
            "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
            "last_verification_error": row.last_verification_error,
            "balance_status": row.balance_status,
            "balance_amount": str(row.balance_amount) if row.balance_amount is not None else None,
            "balance_currency": row.balance_currency,
            "balance_updated_at": row.balance_updated_at.isoformat() if row.balance_updated_at else None,
            "notes": row.notes,
            "supports_balance_sync": _provider_supports_balance_sync(row.provider_code),
        }

    def _validate_provider_code(self, provider_code: str) -> str:
        normalized = provider_code.strip()
        if not normalized:
            raise HTTPException(status_code=422, detail="provider_code_required")
        valid_codes = {item["provider_code"] for item in self.list_provider_options()}
        if normalized not in valid_codes:
            raise HTTPException(status_code=422, detail="provider_code_not_supported")
        return normalized

    def _validate_display_name(self, display_name: str) -> None:
        if not display_name:
            raise HTTPException(status_code=422, detail="provider_account_display_name_required")

    def _normalize_credential_payload(self, payload: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in payload.items():
            key_text = str(key or "").strip()
            value_text = str(value or "").strip()
            if key_text and value_text:
                normalized[key_text] = value_text
        return normalized

    def _normalize_optional_text(self, value: Any) -> str | None:
        return _normalize_optional_text(value)

    def _validate_credentials(self, *, provider_code: str, credential_payload: dict[str, str]) -> None:
        if provider_code == "kling_official":
            api_key = str(credential_payload.get("api_key") or "").strip()
            access_key = str(credential_payload.get("access_key") or "").strip()
            secret_key = str(credential_payload.get("secret_key") or "").strip()
            if api_key or (access_key and secret_key):
                return
            raise HTTPException(status_code=422, detail="provider_account_credentials_incomplete")

        api_key = str(credential_payload.get("api_key") or "").strip()
        if not api_key:
            raise HTTPException(status_code=422, detail="provider_account_api_key_required")

    def _get_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        return user

    def _get_owned_account(
        self,
        *,
        owner_type: str,
        user_id: int | None,
        account_id: int,
    ) -> ProviderAccount:
        query = self.db.query(ProviderAccount).filter(
            ProviderAccount.id == account_id,
            ProviderAccount.owner_type == owner_type,
        )
        if owner_type == OWNER_TYPE_USER:
            query = query.filter(ProviderAccount.user_id == user_id)
        else:
            query = query.filter(ProviderAccount.user_id.is_(None))
        row = query.first()
        if row is None:
            raise HTTPException(status_code=404, detail="provider_account_not_found")
        return row

    def _find_env_synced_platform_account(self, provider_code: str) -> ProviderAccount | None:
        return (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.owner_type == OWNER_TYPE_PLATFORM,
                ProviderAccount.provider_code == provider_code,
                ProviderAccount.notes.like(f"{_ENV_SYNC_NOTES_PREFIX}%"),
            )
            .order_by(ProviderAccount.id.asc())
            .first()
        )

    def _list_env_backed_provider_configs(self) -> list[ProviderConfig]:
        providers: list[ProviderConfig] = []
        for provider in list_providers():
            credentials = {
                key: str(value or "").strip()
                for key, value in provider.auth_config.items()
                if key in {"api_key", "access_key", "secret_key"}
            }
            if not any(credentials.values()):
                continue
            if provider.provider_code in _EXCLUDED_PROVIDER_OPTION_CODES:
                continue
            providers.append(provider)
        return sorted(providers, key=lambda item: item.provider_code)

    def _generate_short_id(self, provider_code: str) -> str:
        alias = _PROVIDER_SHORT_ALIASES.get(provider_code, provider_code[:2].lower() or "pa")
        while True:
            candidate = f"{alias}_{secrets.token_hex(3)}"
            exists = self.db.query(ProviderAccount.id).filter(ProviderAccount.short_id == candidate).first()
            if exists is None:
                return candidate

    def _build_provider_probe_headers(self, provider_code: str, credentials: dict[str, str]) -> dict[str, str]:
        if provider_code == "kling_official":
            api_key = str(credentials.get("api_key") or "").strip()
            if api_key:
                return {"Authorization": f"Bearer {api_key}"}
            return {}
        if provider_code == "vidu_official":
            api_key = str(credentials.get("api_key") or "").strip()
            return {"Authorization": f"Token {api_key}"} if api_key else {}
        api_key = str(credentials.get("api_key") or "").strip()
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _probe_provider_connection(
        self,
        *,
        provider_code: str,
        credentials: dict[str, str],
        base_url_override: str | None,
    ) -> None:
        timeout = httpx.Timeout(15.0)
        if provider_code == "openrouter":
            provider = get_provider(provider_code)
            base_url = _normalize_base_url(base_url_override, provider.base_url)
            url = _join_url(base_url, "/credits")
            response = httpx.get(url, headers=self._build_provider_probe_headers(provider_code, credentials), timeout=timeout)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_verify_failed:{response.text[:240]}")
            return

        if provider_code in {
            "openai_official",
            "yunwu_openai",
            "ksyun_openai",
            "deepseek_official",
            "google_openai_compat",
            "35m",
            "cloudflare_workers_ai",
            "volcengine_seedream",
        }:
            provider = get_provider(provider_code)
            base_url = _normalize_base_url(base_url_override, provider.base_url)
            headers = self._build_provider_probe_headers(provider_code, credentials)
            last_response: httpx.Response | None = None
            for path in _openai_probe_paths(provider_code, base_url):
                url = _join_url(base_url, path)
                response = httpx.get(url, headers=headers, timeout=timeout)
                last_response = response
                if response.status_code < 400:
                    return
            assert last_response is not None
            raise HTTPException(
                status_code=last_response.status_code,
                detail=f"provider_account_verify_failed:{last_response.text[:240]}",
            )

        if provider_code in {"google_official", "google_veo3"}:
            provider = get_provider(provider_code)
            base_url = _normalize_base_url(base_url_override, provider.base_url)
            api_key = str(credentials.get("api_key") or "").strip()
            url = _join_url(base_url, "/v1beta/models")
            response = httpx.get(url, params={"key": api_key}, timeout=timeout)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_verify_failed:{response.text[:240]}")
            return

        if provider_code in {"qwen_official", "wan_official"}:
            provider = get_provider(provider_code)
            base_url = _normalize_base_url(base_url_override, provider.base_url)
            url = _join_url(base_url, "/compatible-mode/v1/models")
            response = httpx.get(url, headers=self._build_provider_probe_headers(provider_code, credentials), timeout=timeout)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_verify_failed:{response.text[:240]}")
            return

        if provider_code == "vidu_official":
            provider = get_provider(provider_code)
            base_url = _normalize_base_url(base_url_override, provider.base_url)
            url = _join_url(base_url, "/ent/v2/credits")
            response = httpx.get(
                url,
                params={"show_detail": "false"},
                headers=self._build_provider_probe_headers(provider_code, credentials),
                timeout=timeout,
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_verify_failed:{response.text[:240]}")
            return

        raise HTTPException(status_code=422, detail="provider_account_verify_not_supported")

    def _fetch_balance(
        self,
        *,
        provider_code: str,
        credentials: dict[str, str],
        base_url_override: str | None,
    ) -> tuple[Decimal, str]:
        provider = get_provider(provider_code)
        base_url = _normalize_base_url(base_url_override, provider.base_url)

        if provider_code == "openrouter":
            url = _join_url(base_url, "/credits")
            response = httpx.get(
                url,
                headers=self._build_provider_probe_headers(provider_code, credentials),
                timeout=httpx.Timeout(15.0),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_balance_sync_failed:{response.text[:240]}")
            payload = response.json()
            total_credits = payload.get("data", {}).get("total_credits") if isinstance(payload, dict) else None
            total_credits = total_credits if total_credits is not None else payload.get("total_credits") if isinstance(payload, dict) else None
            if total_credits is None:
                raise HTTPException(status_code=503, detail="provider_account_balance_sync_failed:balance_not_found")
            return Decimal(str(total_credits)), "USD"

        if provider_code == "vidu_official":
            url = _join_url(base_url, "/ent/v2/credits")
            response = httpx.get(
                url,
                params={"show_detail": "false"},
                headers=self._build_provider_probe_headers(provider_code, credentials),
                timeout=httpx.Timeout(15.0),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=f"provider_account_balance_sync_failed:{response.text[:240]}")
            payload = response.json()
            remains = payload.get("remains") if isinstance(payload, dict) else None
            if not isinstance(remains, list):
                raise HTTPException(status_code=503, detail="provider_account_balance_sync_failed:balance_not_found")
            total_credits = Decimal("0")
            for item in remains:
                if not isinstance(item, dict):
                    continue
                credit_remain = item.get("credit_remain")
                if credit_remain is None:
                    continue
                total_credits += Decimal(str(credit_remain))
            return total_credits, "CREDIT"

        raise HTTPException(status_code=422, detail="provider_account_balance_not_supported")
