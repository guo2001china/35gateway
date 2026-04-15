from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


def _read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        parsed = value.strip()
        if len(parsed) >= 2 and parsed[0] == parsed[-1] and parsed[0] in {'"', "'"}:
            parsed = parsed[1:-1]
        values[key] = parsed
    return values


def _bootstrap_env() -> None:
    for key, value in _read_env_file().items():
        os.environ.setdefault(key, value)
        if key.startswith("API35_"):
            os.environ.setdefault(key.removeprefix("API35_"), value)
        else:
            os.environ.setdefault(f"API35_{key}", value)


_bootstrap_env()


def _normalize_async_database_url(database_url: str) -> str:
    normalized = (database_url or "").strip()
    if not normalized:
        return normalized
    if normalized.startswith("sqlite+pysqlite:///"):
        return normalized.replace("sqlite+pysqlite:///", "sqlite+aiosqlite:///", 1)
    if normalized.startswith("sqlite:///"):
        return normalized.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return normalized


def _parse_proxy_servers(
    *,
    proxy_servers_json: str,
    proxy_server: str,
    proxy_port: str,
    proxy_password: str,
    proxy_cipher: str,
) -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []
    payload = (proxy_servers_json or "").strip()
    if payload:
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, list):
                for index, item in enumerate(parsed, start=1):
                    if not isinstance(item, dict):
                        continue
                    server = str(item.get("server", "")).strip()
                    port = item.get("port")
                    password = str(item.get("password", "")).strip()
                    cipher = str(item.get("cipher") or proxy_cipher or "aes-256-gcm").strip()
                    name = str(item.get("name") or f"server-{index}").strip()
                    if server and port and password:
                        servers.append({
                            "server": server,
                            "port": int(port),
                            "password": password,
                            "cipher": cipher,
                            "name": name,
                        })
        except Exception:
            pass
    if servers:
        return servers
    if proxy_server and proxy_port and proxy_password:
        return [{
            "server": proxy_server,
            "port": int(proxy_port),
            "password": proxy_password,
            "cipher": proxy_cipher or "aes-256-gcm",
            "name": "default",
        }]
    return []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    app_env: str = "dev"
    admin_api_key: str = ""
    site_url: str = ""
    site_console_url: str = ""
    site_biz_qr_url: str = ""
    site_biz_contact_label: str = ""
    site_biz_contact_value: str = ""
    api_prefix: str = ""
    cors_allowed_origins: str = ""
    database_url: str = "sqlite:///./data/35gateway.sqlite3"

    auth_session_ttl_seconds: int = 86400 * 14
    auth_phone_code_ttl_seconds: int = 300
    auth_email_code_ttl_seconds: int = 300
    auth_google_state_ttl_seconds: int = 600
    auth_test_phone: str = "13800000000"
    auth_test_code: str = "123456"
    auth_test_email: str = "test@35m.ai"
    auth_test_email_code: str = "123456"
    auth_sms_provider: str = "local"
    auth_email_provider: str = "local"

    google_auth_client_id: str = ""
    google_auth_client_secret: str = ""
    google_auth_redirect_url: str = ""
    tencent_sms_secret_id: str = ""
    tencent_sms_secret_key: str = ""
    tencent_sms_sdk_app_id: str = ""
    tencent_sms_sign_name: str = ""
    tencent_sms_template_id_login: str = ""
    tencent_sms_region: str = "ap-guangzhou"
    yunpian_sms_api_key: str = ""
    yunpian_sms_sign_name: str = ""
    tencent_email_secret_id: str = ""
    tencent_email_secret_key: str = ""
    tencent_email_region: str = "ap-guangzhou"
    tencent_email_from_email: str = ""
    tencent_email_reply_to: str = ""
    tencent_email_template_id_login: str = ""
    resend_api_key: str = ""
    resend_from_email: str = ""

    power_rate_cny: Decimal = Decimal("1000")
    creem_enabled: bool = False
    creem_env: str = "test"
    creem_api_key: str = ""
    creem_webhook_secret: str = ""
    creem_base_url: str = ""
    creem_success_url: str = ""
    creem_product_starter_9_9: str = ""
    creem_product_growth_29_9: str = ""
    creem_product_studio_99_9: str = ""

    wechat_pay_enabled: bool = False
    wechat_pay_appid: str = ""
    wechat_pay_mch_id: str = ""
    wechat_pay_apiv3_key: str = ""
    wechat_pay_cert_serial_no: str = ""
    wechat_pay_private_key_content: str = ""
    wechat_pay_notify_url: str = ""
    wechat_pay_order_expire_minutes: int = 30
    wechat_pay_public_key: str = ""
    wechat_pay_public_key_id: str = ""
    wechat_pay_platform_cert_content: str = ""

    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_key_prefix: str = "uploads"
    oss_upload_expire_seconds: int = 600
    oss_signed_url_expire_seconds: int = 3600
    oss_max_file_size: int = 104857600

    file_storage_mode: str = "local"
    cloud_upload_sign_url: str = ""
    web_backend_url: str = "http://127.0.0.1:8025"
    web_frontend_url: str = ""
    api35_base_url: str = "http://127.0.0.1:8025"
    session_me_cache_ttl_seconds: float = 15.0
    proxy_server: str = ""
    proxy_port: str = ""
    proxy_password: str = ""
    proxy_cipher: str = "aes-256-gcm"
    proxy_servers_json: str = ""

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        raw_value = self.cors_allowed_origins.strip()
        if not raw_value:
            return []
        if raw_value == "*":
            return ["*"]
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    @property
    def async_database_url(self) -> str:
        return _normalize_async_database_url(self.database_url)

    @property
    def database_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def proxy_servers(self) -> list[dict[str, Any]]:
        return _parse_proxy_servers(
            proxy_servers_json=self.proxy_servers_json,
            proxy_server=self.proxy_server,
            proxy_port=self.proxy_port,
            proxy_password=self.proxy_password,
            proxy_cipher=self.proxy_cipher,
        )

    @property
    def proxy_enabled(self) -> bool:
        return bool(self.proxy_servers)


settings = Settings()
