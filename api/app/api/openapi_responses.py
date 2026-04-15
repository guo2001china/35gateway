from __future__ import annotations

from app.api.schemas import ErrorResponse


def error_response(description: str, detail_example: str) -> dict:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "detail": detail_example,
                }
            }
        },
    }


AUTH_ERROR_RESPONSES = {
    401: error_response("缺少或无效的 API Key。", "invalid_api_key"),
}

USER_AUTH_ERROR_RESPONSES = {
    401: error_response("缺少或无效的用户凭证。", "invalid_user_auth"),
}

SESSION_AUTH_ERROR_RESPONSES = {
    401: error_response("缺少或无效的浏览器会话。", "invalid_session_token"),
}

MODEL_NOT_FOUND_RESPONSE = {
    404: error_response("模型不存在。", "model_not_found"),
}

TASK_NOT_FOUND_RESPONSE = {
    404: error_response("任务不存在或无权访问。", "task_not_found"),
}

COMMON_ESTIMATE_ERROR_RESPONSES = {
    402: error_response("算力余额不足。", "insufficient_balance"),
    403: error_response("账户未激活。", "account_not_active"),
    429: error_response("请求频率超限。", "rate_limited"),
    503: error_response("当前没有可用供应商。", "no_available_provider"),
}

MODEL_PROVIDER_ERROR_RESPONSES = {
    400: error_response("指标时间窗口不支持。", "unsupported_window"),
    404: error_response("模型不存在。", "model_not_found"),
}

FILE_UPLOAD_ERROR_RESPONSES = {
    403: error_response("用户未激活。", "user_not_active"),
    404: error_response("文件不存在。", "file_not_found"),
    422: error_response("文件参数不合法。", "invalid_file_size"),
    502: error_response("OSS 上传或校验失败。", "oss_file_verify_failed"),
    503: error_response("OSS 未配置。", "oss_not_configured"),
}

PROVIDER_API_ERROR_RESPONSES = {
    402: error_response("算力余额不足。", "insufficient_balance"),
    403: error_response("用户未激活。", "account_not_active"),
    404: error_response("文件或模型不存在。", "file_not_found"),
    422: error_response("请求参数不合法。", "invalid_request_payload"),
    502: error_response("上游供应商请求失败。", "provider_request_failed"),
    503: error_response("供应商未配置或暂不可用。", "provider_not_configured"),
}
