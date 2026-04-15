from __future__ import annotations

import httpx

from app.core.config import settings


class ResendEmailError(RuntimeError):
    pass


class ResendEmailService:
    base_url = "https://api.resend.com"

    def __init__(self) -> None:
        self.api_key = settings.resend_api_key.strip()
        self.from_email = settings.resend_from_email.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.from_email)

    def send_login_code(self, *, email: str, code: str, ttl_seconds: int) -> None:
        if not self.is_configured():
            raise ResendEmailError("resend_email_not_configured")

        ttl_minutes = max(1, ttl_seconds // 60)
        subject = "35m.ai 登录验证码"
        text = (
            f"你的 35m.ai 登录验证码是 {code}，请在 {ttl_minutes} 分钟内完成验证。"
            "如果不是你本人操作，请忽略这封邮件。"
        )
        html = (
            "<div style=\"font-family:Inter,Helvetica,Arial,sans-serif;color:#0f172a;line-height:1.6;\">"
            "<h2 style=\"margin:0 0 12px;font-size:22px;\">35m.ai 登录验证码</h2>"
            f"<p style=\"margin:0 0 12px;\">你的验证码是：</p>"
            f"<div style=\"display:inline-block;padding:12px 18px;border-radius:12px;background:#eff6ff;"
            "border:1px solid rgba(37,99,235,0.16);font-size:28px;font-weight:700;letter-spacing:0.16em;\">"
            f"{code}</div>"
            f"<p style=\"margin:16px 0 0;\">请在 {ttl_minutes} 分钟内完成验证。如果不是你本人操作，请忽略这封邮件。</p>"
            "</div>"
        )
        payload = {
            "from": self.from_email,
            "to": [email],
            "subject": subject,
            "text": text,
            "html": html,
        }

        try:
            response = httpx.post(
                f"{self.base_url}/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise ResendEmailError("resend_email_unavailable") from exc

        if response.status_code >= 400:
            detail = "resend_email_send_failed"
            try:
                data = response.json()
                message = data.get("message")
                if isinstance(message, str) and message:
                    detail = message
            except ValueError:
                pass
            raise ResendEmailError(detail)
