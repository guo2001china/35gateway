from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from app.api.schemas.common import OpenSchemaModel


class OpenAIChatMessage(OpenSchemaModel):
    role: str = Field(description="消息角色，例如 system、user、assistant。")
    content: Any = Field(description="消息内容，可为纯文本或结构化内容。")


class OpenAIChatCompletionsRequest(OpenSchemaModel):
    model: str = Field(description="平台公开文本模型码，例如 `gpt-5.4`。")
    messages: list[OpenAIChatMessage] = Field(description="发送给模型的对话消息数组。")
    temperature: float | None = Field(default=None, description="可选采样温度。")
    max_tokens: int | None = Field(default=None, description="可选输出 token 上限。")
    stream: bool | None = Field(default=None, description="是否按流式返回。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "model": "gpt-5.4",
                "messages": [{"role": "user", "content": "用一句话介绍 35m.ai"}],
                "temperature": 0.7,
            }
        },
    )


class OpenAIChatChoiceMessage(OpenSchemaModel):
    role: str | None = Field(default=None, description="模型返回消息的角色。")
    content: Any = Field(default=None, description="模型返回的消息内容。")


class OpenAIChatChoice(OpenSchemaModel):
    index: int | None = Field(default=None, description="候选结果下标。")
    message: OpenAIChatChoiceMessage | None = Field(default=None, description="候选结果中的消息体。")
    finish_reason: str | None = Field(default=None, description="生成结束原因。")


class OpenAIUsage(OpenSchemaModel):
    prompt_tokens: int | None = Field(default=None, description="输入消耗的 token 数。")
    completion_tokens: int | None = Field(default=None, description="输出消耗的 token 数。")
    total_tokens: int | None = Field(default=None, description="总 token 数。")


class OpenAIChatCompletionsResponse(OpenSchemaModel):
    id: str | None = Field(default=None, description="上游返回的响应 ID。")
    object: str | None = Field(default=None, description="响应对象类型，通常为 chat.completion。")
    created: int | None = Field(default=None, description="Unix 时间戳。")
    model: str | None = Field(default=None, description="实际命中的模型。")
    choices: list[OpenAIChatChoice] = Field(default_factory=list, description="候选回复列表。")
    usage: OpenAIUsage | None = Field(default=None, description="Token 使用量。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "id": "chatcmpl_123",
                "object": "chat.completion",
                "created": 1773571200,
                "model": "gpt-5.4",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "35m.ai 是一个聚合文本、图片与视频模型调用的平台。",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30},
            }
        },
    )


class OpenAIResponsesRequest(OpenSchemaModel):
    model: str = Field(description="平台公开文本模型码，例如 `gpt-5.4-pro`。")
    input: Any = Field(description="Responses API 输入，支持字符串、结构化输入数组等。")
    instructions: str | None = Field(default=None, description="可选系统/开发者指令。")
    max_output_tokens: int | None = Field(default=None, description="可选输出 token 上限。")
    stream: bool | None = Field(default=None, description="是否按流式返回。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "model": "gpt-5.4-pro",
                "input": "用一句话介绍 35m.ai 的定位。",
                "instructions": "回答简洁。",
            }
        },
    )


class OpenAIResponsesUsage(OpenSchemaModel):
    input_tokens: int | None = Field(default=None, description="输入 token 数。")
    output_tokens: int | None = Field(default=None, description="输出 token 数。")
    total_tokens: int | None = Field(default=None, description="总 token 数。")

    model_config = ConfigDict(extra="allow")


class OpenAIResponsesResponse(OpenSchemaModel):
    id: str | None = Field(default=None, description="上游返回的响应 ID。")
    object: str | None = Field(default=None, description="响应对象类型，通常为 response。")
    created_at: int | None = Field(default=None, description="Unix 时间戳。")
    status: str | None = Field(default=None, description="响应状态。")
    model: str | None = Field(default=None, description="实际命中的模型。")
    output: list[Any] = Field(default_factory=list, description="Responses API 输出数组。")
    output_text: str | None = Field(default=None, description="聚合后的纯文本输出。")
    usage: OpenAIResponsesUsage | None = Field(default=None, description="Token 使用量。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "id": "resp_123",
                "object": "response",
                "created_at": 1773571200,
                "status": "completed",
                "model": "gpt-5.4-pro",
                "output_text": "35m.ai 是统一聚合多类模型能力的 API 网关。",
                "usage": {"input_tokens": 12, "output_tokens": 16, "total_tokens": 28},
            }
        },
    )


class GeminiPart(OpenSchemaModel):
    text: str | None = Field(default=None, description="Gemini 输入中的文本片段。")


class GeminiContent(OpenSchemaModel):
    role: str | None = Field(default=None, description="可选 Gemini 角色，通常为 user 或 model。")
    parts: list[GeminiPart] = Field(description="Gemini 内容片段数组。")


class GeminiGenerateContentRequest(OpenSchemaModel):
    contents: list[GeminiContent] = Field(description="Gemini 请求内容数组。")
    generationConfig: dict[str, Any] | None = Field(
        default=None,
        description="可选 Gemini 生成配置。",
    )
    safetySettings: list[dict[str, Any]] | None = Field(
        default=None,
        description="可选 Gemini 安全设置。",
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": "用一句话解释请求前预计费的作用。"}],
                    }
                ]
            }
        },
    )


class GeminiResponsePart(OpenSchemaModel):
    text: str | None = Field(default=None, description="Gemini 返回的文本片段。")


class GeminiResponseContent(OpenSchemaModel):
    role: str | None = Field(default=None, description="Gemini 返回内容的角色。")
    parts: list[GeminiResponsePart] = Field(default_factory=list, description="Gemini 返回内容片段。")


class GeminiCandidate(OpenSchemaModel):
    content: GeminiResponseContent | None = Field(default=None, description="候选内容。")
    finishReason: str | None = Field(default=None, description="Gemini 候选结束原因。")
    index: int | None = Field(default=None, description="候选下标。")


class GeminiUsageMetadata(OpenSchemaModel):
    promptTokenCount: int | None = Field(default=None, description="输入 token 数。")
    candidatesTokenCount: int | None = Field(default=None, description="候选输出 token 数。")
    totalTokenCount: int | None = Field(default=None, description="总 token 数。")


class GeminiGenerateContentResponse(OpenSchemaModel):
    candidates: list[GeminiCandidate] = Field(default_factory=list, description="Gemini 候选结果列表。")
    usageMetadata: GeminiUsageMetadata | None = Field(default=None, description="Gemini 用量信息。")
    modelVersion: str | None = Field(default=None, description="Gemini 返回的模型版本。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "candidates": [
                    {
                        "index": 0,
                        "content": {
                            "role": "model",
                            "parts": [{"text": "请求前预计费会先测算价格和算力，不真正创建任务。"}],
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 15,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 35,
                },
                "modelVersion": "gemini-2.5-pro",
            }
        },
    )
