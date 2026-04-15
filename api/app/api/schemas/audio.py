from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from app.api.schemas.common import OpenSchemaModel
from app.core.provider_catalog.qwen_voices import (
    QWEN_SYSTEM_TTS_MODE_STANDARD,
)


class QwenSystemTtsRequest(OpenSchemaModel):
    text: str = Field(description="待合成文本。")
    voice: str = Field(description="要使用的系统音色，必须来自 `GET /v1/qwen/system-voices`。")
    mode: str = Field(
        default=QWEN_SYSTEM_TTS_MODE_STANDARD,
        description="系统音色合成模式。当前支持 `standard` 与 `instruct`。",
    )
    language_type: str | None = Field(
        default=None,
        description="可选语言类型，建议与输入文本语言一致，例如 `Chinese`、`English`。",
    )
    instructions: str | None = Field(
        default=None,
        description="可选自然语言语音控制指令。当前仅 `mode=instruct` 支持。",
    )
    optimize_instructions: bool | None = Field(
        default=None,
        description="是否启用指令优化。当前仅 `mode=instruct` 支持。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "text": "欢迎来到 35m.ai，这是一段用于品牌旁白的中文示例。",
                "voice": "Diana",
                "mode": QWEN_SYSTEM_TTS_MODE_STANDARD,
                "language_type": "Chinese",
            }
        },
    )


class QwenClonedTtsRequest(OpenSchemaModel):
    text: str = Field(description="待合成文本。")
    voice: str = Field(description="要使用的 cloned voice，必须来自 `GET /v1/qwen/voice-clones`。")
    language_type: str | None = Field(
        default=None,
        description="可选语言类型，建议与输入文本语言一致，例如 `Chinese`、`English`。",
    )
    instructions: str | None = Field(
        default=None,
        description="当前 cloned voice 模式不支持该字段，传入会被拒绝。",
    )
    optimize_instructions: bool | None = Field(
        default=None,
        description="当前 cloned voice 模式不支持该字段，传入会被拒绝。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "text": "欢迎来到 35m.ai，这是一段用于品牌旁白的中文示例。",
                "voice": "brand_voice",
                "language_type": "Chinese",
            }
        },
    )


class QwenAudioOutput(OpenSchemaModel):
    url: str | None = Field(default=None, description="上游返回的音频下载地址，通常有效 24 小时。")
    expires_at: int | str | None = Field(default=None, description="音频下载地址过期时间。")


class QwenTtsOutput(OpenSchemaModel):
    audio: QwenAudioOutput | None = Field(default=None, description="音频输出对象。")
    finish_reason: str | None = Field(default=None, description="结束原因。")


class QwenTtsResponse(OpenSchemaModel):
    request_id: str | None = Field(default=None, description="Qwen 请求 ID。")
    voice: str | None = Field(default=None, description="本次使用的 voice。")
    mode: str | None = Field(default=None, description="system TTS 模式。cloned TTS 不返回该字段。")
    output: QwenTtsOutput | None = Field(default=None, description="Qwen 输出对象。")
    usage: dict[str, Any] | None = Field(default=None, description="上游返回的 usage 信息。")


class QwenVoiceCloneCreateRequest(OpenSchemaModel):
    name: str = Field(
        description="音色别名，只允许字母、数字和下划线，且不超过 16 个字符。",
        pattern=r"^[A-Za-z0-9_]{1,16}$",
    )
    audio_url: str = Field(description="可直接被 Qwen 拉取的音频 URL。")
    text: str | None = Field(default=None, description="可选参考文本。")
    language: str | None = Field(default=None, description="可选音频语言，例如 `zh`、`en`。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "brand_voice",
                "audio_url": "https://example.com/brand-voice.wav",
                "language": "zh",
            }
        },
    )


class QwenVoiceCloneResponse(OpenSchemaModel):
    request_id: str | None = Field(default=None, description="Qwen 请求 ID。")
    voice: str | None = Field(default=None, description="创建出的可复用 voice 标识。")
    name: str | None = Field(default=None, description="本次提交的 voice 名称。")
    usage: dict[str, Any] | None = Field(default=None, description="上游 usage 信息。")


class QwenVoiceListItem(OpenSchemaModel):
    voice: str | None = Field(default=None, description="可直接用于 Qwen TTS 的 voice。")
    gmt_create: str | None = Field(default=None, description="创建时间。")


class QwenVoiceListResponse(OpenSchemaModel):
    request_id: str | None = Field(default=None, description="Qwen 请求 ID。")
    items: list[QwenVoiceListItem] = Field(default_factory=list, description="当前页 voice 列表。")
    page_index: int = Field(default=0, description="当前页索引。")
    page_size: int = Field(default=10, description="当前页大小。")
    usage: dict[str, Any] | None = Field(default=None, description="上游 usage 信息。")


class QwenSystemVoiceItem(OpenSchemaModel):
    voice: str = Field(description="Qwen 系统音色的 voice 标识。")
    locale: str | None = Field(default=None, description="平台整理的语言或方言标签。")
    languages: list[str] = Field(default_factory=list, description="平台整理的语种列表。")
    description: str | None = Field(default=None, description="平台整理的音色说明。")
    modes: list[str] = Field(default_factory=list, description="该系统音色当前可用于 35m 的合成模式。")


class QwenSystemVoiceListResponse(OpenSchemaModel):
    items: list[QwenSystemVoiceItem] = Field(
        default_factory=list,
        description="平台按官方文档维护并按 35m 规则整理后的系统音色目录。",
    )
    total: int = Field(default=0, description="当前查询条件下的音色总数。")
    page_index: int = Field(default=0, description="当前页索引。")
    page_size: int = Field(default=10, description="当前页大小。")


class QwenVoiceDeleteResponse(OpenSchemaModel):
    request_id: str | None = Field(default=None, description="Qwen 请求 ID。")
    voice: str | None = Field(default=None, description="被删除的 voice。")
    deleted: bool = Field(default=False, description="是否已删除。")


class MiniMaxVoiceSetting(OpenSchemaModel):
    voice_id: str = Field(
        description="要使用的 MiniMax voice_id。",
        pattern=r"^[A-Za-z][A-Za-z0-9_-]{6,254}[A-Za-z0-9]$",
    )
    speed: float | None = Field(default=None, description="语速倍率。")
    vol: float | None = Field(default=None, description="音量倍率。")
    pitch: float | None = Field(default=None, description="音高倍率。")


class MiniMaxAudioSetting(OpenSchemaModel):
    audio_sample_rate: int | None = Field(default=None, description="采样率。")
    bitrate: int | None = Field(default=None, description="比特率。")
    format: str | None = Field(default=None, description="输出格式，如 `mp3`、`wav`。")
    channel: int | None = Field(default=None, description="声道数。")


class MiniMaxTtsVoiceControl(OpenSchemaModel):
    speed: float | None = Field(default=None, description="语速倍率。")
    vol: float | None = Field(default=None, description="音量倍率。")
    pitch: float | None = Field(default=None, description="音高倍率。")


class MiniMaxBaseTtsRequest(OpenSchemaModel):
    model: Literal["speech-2.8-hd", "speech-2.8-turbo"] = Field(
        default="speech-2.8-hd",
        description="MiniMax 语音模型，当前支持 `speech-2.8-hd` 和 `speech-2.8-turbo`。",
    )
    text: str | None = Field(default=None, description="要合成的长文本。可与 `text_file_id` 二选一。")
    text_file_id: int | None = Field(
        default=None,
        description="已上传到 MiniMax File API 的文本文件 `file_id`。可与 `text` 二选一。",
    )
    voice_id: str = Field(
        description="要使用的 MiniMax voice_id。",
        pattern=r"^[A-Za-z][A-Za-z0-9_-]{6,254}[A-Za-z0-9]$",
    )
    voice_setting: MiniMaxTtsVoiceControl | None = Field(default=None, description="MiniMax 语音调节设置。")
    audio_setting: MiniMaxAudioSetting | None = Field(default=None, description="MiniMax 音频输出设置。")
    language_boost: str | None = Field(default=None, description="可选语言增强设置，例如 `English` 或 `auto`。")
    pronunciation_dict: dict[str, Any] | None = Field(default=None, description="可选发音字典。")
    subtitle_enable: bool | None = Field(default=None, description="是否开启字幕输出。")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_text_source(self) -> "MiniMaxBaseTtsRequest":
        if not self.text and self.text_file_id is None:
            raise ValueError("text_or_text_file_id_required")
        return self


class MiniMaxSystemTtsRequest(MiniMaxBaseTtsRequest):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "model": "speech-2.8-hd",
                "text": "This is an async long-form speech generation example from 35m.ai.",
                "voice_id": "English_expressive_narrator",
                "language_boost": "English",
                "voice_setting": {
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0,
                },
                "audio_setting": {
                    "audio_sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 2,
                },
            }
        },
    )


class MiniMaxClonedTtsRequest(MiniMaxBaseTtsRequest):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "model": "speech-2.8-hd",
                "text": "This is an async cloned-voice speech generation example from 35m.ai.",
                "voice_id": "MiniMaxClone1773992276",
                "voice_setting": {
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0,
                },
                "audio_setting": {
                    "audio_sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 2,
                },
            }
        },
    )


class MiniMaxT2AAsyncRequest(OpenSchemaModel):
    model: Literal["speech-2.8-hd", "speech-2.8-turbo"] = Field(
        default="speech-2.8-hd",
        description="当前支持 `speech-2.8-hd` 和 `speech-2.8-turbo`。",
    )
    text: str | None = Field(default=None, description="要合成的长文本。可与 `text_file_id` 二选一。")
    text_file_id: int | None = Field(
        default=None,
        description="已上传到 MiniMax File API 的文本文件 `file_id`。可与 `text` 二选一。",
    )
    voice_setting: MiniMaxVoiceSetting = Field(description="MiniMax 语音设置。")
    audio_setting: MiniMaxAudioSetting | None = Field(default=None, description="MiniMax 音频输出设置。")
    language_boost: str | None = Field(default=None, description="可选语言增强设置，例如 `English` 或 `auto`。")
    pronunciation_dict: dict[str, Any] | None = Field(default=None, description="可选发音字典。")
    subtitle_enable: bool | None = Field(default=None, description="是否开启字幕输出。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "model": "speech-2.8-hd",
                "text": "This is an async long-form speech generation example from 35m.ai.",
                "language_boost": "English",
                "voice_setting": {
                    "voice_id": "English_expressive_narrator",
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0,
                },
                "audio_setting": {
                    "audio_sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 2,
                },
            }
        },
    )

    @model_validator(mode="after")
    def validate_text_source(self) -> "MiniMaxT2AAsyncRequest":
        if not self.text and self.text_file_id is None:
            raise ValueError("text_or_text_file_id_required")
        return self


class MiniMaxT2AAsyncTaskResponse(OpenSchemaModel):
    id: str | None = Field(default=None, description="平台任务 ID。")
    provider_task_id: str | None = Field(default=None, description="MiniMax task_id。")
    status: str | None = Field(default=None, description="任务状态。")
    provider_status: str | None = Field(default=None, description="MiniMax 原始状态。")
    model: str | None = Field(default=None, description="模型名。")
    voice_id: str | None = Field(default=None, description="当前任务使用的 voice_id。")
    voice_type: str | None = Field(default=None, description="当前任务使用的音色类型，例如 `system` 或 `voice_cloning`。")
    file_id: str | None = Field(default=None, description="MiniMax file_id。")
    usage_characters: int | None = Field(default=None, description="MiniMax 返回的 billed characters。")
    created_at: int | None = Field(default=None, description="Unix 时间戳。")
    provider_raw: dict[str, Any] | None = Field(default=None, description="上游原始响应。")


class MiniMaxVoiceCloneRequest(OpenSchemaModel):
    voice_id: str = Field(
        description="要创建的 MiniMax voice_id。",
        pattern=r"^[A-Za-z][A-Za-z0-9_-]{6,254}[A-Za-z0-9]$",
    )
    audio_url: str = Field(description="可直接下载的主参考音频 URL，平台会先上传到 MiniMax File API。")
    prompt_audio_url: str = Field(description="可直接下载的短提示音频 URL，平台会先上传到 MiniMax File API。")
    prompt_text: str = Field(description="与 `prompt_audio_url` 对应的文字转写。")
    text: str | None = Field(default=None, description="可选预览文本；如果传入，上游会返回 demo_audio。")
    need_noise_reduction: bool | None = Field(default=None, description="是否开启降噪。")
    need_volume_normalization: bool | None = Field(default=None, description="是否开启音量归一化。")
    language_boost: str | None = Field(default=None, description="可选语言增强设置。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "voice_id": "MiniMaxDemo01",
                "audio_url": "https://example.com/voice-clone-source.wav",
                "prompt_audio_url": "https://example.com/voice-clone-prompt.wav",
                "prompt_text": "This voice sounds natural and pleasant.",
                "text": "This is the preview text for the cloned voice.",
                "need_noise_reduction": False,
                "need_volume_normalization": False,
            }
        },
    )


class MiniMaxVoiceCloneResponse(OpenSchemaModel):
    voice_id: str | None = Field(default=None, description="创建的 MiniMax voice_id。")
    model: str | None = Field(default=None, description="用于克隆的模型。")
    demo_audio: str | None = Field(default=None, description="如果上游返回预览音频，会出现在这里。")
    input_sensitive: Any = Field(default=None, description="上游安全检测结果。")
    input_sensitive_type: Any = Field(default=None, description="上游安全检测类型。")
    provider_raw: dict[str, Any] | None = Field(default=None, description="上游原始响应。")


class MiniMaxVoiceItem(OpenSchemaModel):
    voice_id: str | None = Field(default=None, description="MiniMax voice_id。")
    voice_name: str | None = Field(default=None, description="系统音色名称。")
    description: list[str] | None = Field(default=None, description="音色描述。")
    created_time: str | None = Field(default=None, description="创建时间。")


class MiniMaxVoiceCatalogResponse(OpenSchemaModel):
    items: list[MiniMaxVoiceItem] = Field(default_factory=list, description="当前查询条件下的音色列表。")
    total: int = Field(default=0, description="当前查询条件下的音色总数。")
    page_index: int = Field(default=0, description="当前页索引。")
    page_size: int = Field(default=10, description="当前页大小。")


class MiniMaxVoiceListResponse(OpenSchemaModel):
    system_voice: list[MiniMaxVoiceItem] = Field(default_factory=list, description="系统音色列表。")
    voice_cloning: list[MiniMaxVoiceItem] = Field(default_factory=list, description="快速克隆音色列表。")
    voice_generation: list[MiniMaxVoiceItem] = Field(default_factory=list, description="生成音色列表。")
    provider_raw: dict[str, Any] | None = Field(default=None, description="上游原始响应。")


class MiniMaxVoiceDeleteResponse(OpenSchemaModel):
    voice_id: str | None = Field(default=None, description="被删除的 voice_id。")
    deleted: bool = Field(default=False, description="是否已删除。")
