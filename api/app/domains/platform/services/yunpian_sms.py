from __future__ import annotations

from math import ceil

import httpx

from app.core.config import settings


class YunpianSmsError(RuntimeError):
    pass


class YunpianSmsService:
    endpoint = "https://sms.yunpian.com/v2/sms/single_send.json"

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.yunpian_sms_api_key and settings.yunpian_sms_sign_name)

    def send_login_code(self, *, phone: str, code: str, ttl_seconds: int) -> None:
        if not self.is_configured():
            raise YunpianSmsError("yunpian_sms_not_configured")

        ttl_minutes = max(1, ceil(ttl_seconds / 60))
        text = (
            f"{self._format_sign(settings.yunpian_sms_sign_name)}"
            f"您的验证码是{code}，请在{ttl_minutes}分钟内完成验证。如非本人操作，请忽略本短信。"
        )
        payload = {
            "apikey": settings.yunpian_sms_api_key,
            "mobile": self._format_phone(phone),
            "text": text,
        }

        try:
            response = httpx.post(self.endpoint, data=payload, timeout=10)
        except httpx.HTTPError as exc:
            raise YunpianSmsError("yunpian_sms_request_failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise YunpianSmsError("yunpian_sms_invalid_response") from exc

        code_value = int(data.get("code", -1))
        if code_value != 0:
            message = str(data.get("msg") or code_value or "unknown_error")
            raise YunpianSmsError(f"yunpian_sms_send_failed:{message}")

    @staticmethod
    def _format_sign(sign_name: str) -> str:
        normalized = sign_name.strip()
        if normalized.startswith("【") and normalized.endswith("】"):
            return normalized
        return f"【{normalized}】"

    @staticmethod
    def _format_phone(phone: str) -> str:
        normalized = phone.strip()
        if normalized.startswith("+86"):
            return normalized[3:]
        if normalized.startswith("+"):
            raise YunpianSmsError("yunpian_sms_only_supports_cn_mainland_phone")
        return normalized
