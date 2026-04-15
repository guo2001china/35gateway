from __future__ import annotations

from math import ceil

from app.core.config import settings


class TencentSmsError(RuntimeError):
    pass


class TencentSmsService:
    @staticmethod
    def is_configured() -> bool:
        return all(
            [
                settings.tencent_sms_secret_id,
                settings.tencent_sms_secret_key,
                settings.tencent_sms_sdk_app_id,
                settings.tencent_sms_sign_name,
                settings.tencent_sms_template_id_login,
            ]
        )

    def send_login_code(self, *, phone: str, code: str, ttl_seconds: int) -> None:
        if not self.is_configured():
            raise TencentSmsError("tencent_sms_not_configured")

        try:
            from tencentcloud.common import credential
            from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
                TencentCloudSDKException,
            )
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.sms.v20210111 import models, sms_client
        except ImportError as exc:
            raise TencentSmsError("tencent_sms_sdk_not_installed") from exc

        cred = credential.Credential(settings.tencent_sms_secret_id, settings.tencent_sms_secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "sms.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = sms_client.SmsClient(cred, settings.tencent_sms_region, client_profile)

        request = models.SendSmsRequest()
        request.SmsSdkAppId = settings.tencent_sms_sdk_app_id
        request.SignName = settings.tencent_sms_sign_name
        request.TemplateId = settings.tencent_sms_template_id_login
        request.PhoneNumberSet = [self._format_phone(phone)]
        request.TemplateParamSet = [code, str(max(1, ceil(ttl_seconds / 60)))]

        try:
            response = client.SendSms(request)
        except TencentCloudSDKException as exc:
            raise TencentSmsError(f"tencent_sms_request_failed:{exc}") from exc

        send_statuses = getattr(response, "SendStatusSet", None) or []
        if not send_statuses:
            raise TencentSmsError("tencent_sms_empty_response")

        first_status = send_statuses[0]
        code_value = str(getattr(first_status, "Code", "") or "")
        if code_value != "Ok":
            message = str(getattr(first_status, "Message", "") or code_value or "unknown_error")
            raise TencentSmsError(f"tencent_sms_send_failed:{message}")

    @staticmethod
    def _format_phone(phone: str) -> str:
        if phone.startswith("+"):
            return phone
        return f"+86{phone}"
