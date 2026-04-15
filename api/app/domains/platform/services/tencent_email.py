from __future__ import annotations

import json
from math import ceil

from app.core.config import settings


class TencentEmailError(RuntimeError):
    pass


class TencentEmailService:
    subject = "35m.ai 登录验证码"

    @staticmethod
    def is_configured() -> bool:
        return all(
            [
                settings.tencent_email_secret_id,
                settings.tencent_email_secret_key,
                settings.tencent_email_from_email,
                settings.tencent_email_template_id_login,
            ]
        )

    def send_login_code(self, *, email: str, code: str, ttl_seconds: int) -> None:
        if not self.is_configured():
            raise TencentEmailError("tencent_email_not_configured")

        try:
            template_id = int(settings.tencent_email_template_id_login)
        except ValueError as exc:
            raise TencentEmailError("tencent_email_template_id_invalid") from exc

        try:
            from tencentcloud.common import credential
            from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
                TencentCloudSDKException,
            )
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.ses.v20201002 import models, ses_client
        except ImportError as exc:
            raise TencentEmailError("tencent_email_sdk_not_installed") from exc

        cred = credential.Credential(settings.tencent_email_secret_id, settings.tencent_email_secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "ses.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = ses_client.SesClient(cred, settings.tencent_email_region, client_profile)

        request = models.SendEmailRequest()
        request.FromEmailAddress = settings.tencent_email_from_email
        request.Destination = [email]
        request.Subject = self.subject
        request.TriggerType = 1
        if settings.tencent_email_reply_to:
            request.ReplyToAddresses = settings.tencent_email_reply_to

        template = models.Template()
        template.TemplateID = template_id
        template.TemplateData = json.dumps(
            {
                "code": code,
                "ttl_minutes": max(1, ceil(ttl_seconds / 60)),
            },
            ensure_ascii=False,
        )
        request.Template = template

        try:
            response = client.SendEmail(request)
        except TencentCloudSDKException as exc:
            message = str(exc) or exc.__class__.__name__
            raise TencentEmailError(f"tencent_email_send_failed:{message}") from exc

        if not str(getattr(response, "MessageId", "") or "").strip():
            raise TencentEmailError("tencent_email_empty_response")
