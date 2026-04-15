from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from app.api.schemas.common import OpenSchemaModel


class VeoRequest(OpenSchemaModel):
    prompt: str = Field(description="视频提示词。官网公开契约以 Google 官方 Veo 参数为准，其他供应商按同一契约适配。")
    input_reference: str | None = Field(
        default=None,
        description="可选初始图片输入，用于图生视频。",
    )
    first_frame: str | None = Field(default=None, description="可选首帧输入。")
    last_frame: str | None = Field(default=None, description="可选尾帧输入。")
    reference_images: list[str] | None = Field(
        default=None,
        description="可选参考图列表。Google 官方当前上限为 3 张，用于主体一致性。",
    )
    video_url: str | None = Field(
        default=None,
        description="可选原视频 URL，用于视频延展模式。当前主要由 Google 官方 Veo 3.1 系列承接，并非所有供应商或模式都支持。",
    )
    resolution: str | None = Field(
        default=None,
        description="目标分辨率。常见值：`720p`、`1080p`、`4k`。",
        json_schema_extra={"enum": ["720p", "1080p", "4k"]},
    )
    aspect_ratio: str | None = Field(
        default=None,
        description="目标宽高比。常见值：`16:9`、`9:16`。",
        json_schema_extra={"enum": ["16:9", "9:16"]},
    )
    seconds: int | None = Field(
        default=None,
        description="目标时长，单位秒。Veo 官方当前常见取值为 `4`、`6`、`8`。",
        json_schema_extra={"enum": [4, 6, 8]},
    )
    generate_audio: bool | None = Field(
        default=None,
        description="当供应商支持时，是否同时生成音频。可选值：`true`、`false`。非官方供应商不支持时会忽略。",
    )
    number_of_videos: int | None = Field(
        default=None,
        description="可选生成数量。Google 官方支持该能力；其他供应商不支持时会忽略。",
    )
    person_generation: str | None = Field(
        default=None,
        description="可选人物生成策略。当前主要用于 Google 官方 Veo 系列，其他供应商不支持时会忽略。",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="可选负向提示词。",
    )
    seed: int | None = Field(
        default=None,
        description="可选随机种子。Google 官方和部分适配供应商支持；不支持时会忽略。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "一段镜头运动顺滑的时尚广告视频。",
                "reference_images": [
                    "https://example.com/model-front.png",
                    "https://example.com/model-side.png",
                ],
                "resolution": "1080p",
                "aspect_ratio": "16:9",
                "seconds": 8,
                "generate_audio": True,
            }
        },
    )


class SeedanceRequest(OpenSchemaModel):
    prompt: str = Field(description="视频提示词。当前 V1 公开支持文生视频和单图生视频。")
    input_reference: str | None = Field(
        default=None,
        description="可选单图输入，用于图生视频。",
    )
    resolution: str | None = Field(
        default=None,
        description="目标分辨率。Seedance 2.0 V1 当前只对外开放 `720p`。",
        json_schema_extra={"enum": ["720p"]},
    )
    aspect_ratio: str | None = Field(
        default=None,
        description="目标宽高比。支持 `auto`、`21:9`、`16:9`、`4:3`、`1:1`、`3:4`、`9:16`。",
        json_schema_extra={"enum": ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]},
    )
    seconds: int | None = Field(
        default=None,
        description="目标时长，单位秒。Seedance 2.0 当前支持 `4-15` 秒。",
    )
    generate_audio: bool | None = Field(
        default=None,
        description="是否生成同步音频。上游默认开启，价格不因该开关变化。",
    )
    seed: int | None = Field(
        default=None,
        description="可选随机种子。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "电影感十足的产品广告镜头，镜头缓慢推近，环境音真实同步。",
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "seconds": 4,
                "generate_audio": True,
            }
        },
    )


class MiniMaxVideoRequest(OpenSchemaModel):
    prompt: str | None = Field(default=None, description="视频提示词。文生模式必填；图生和首尾帧模式可选。")
    input_reference: str | None = Field(
        default=None,
        description="可选初始图片输入，用于图生视频。",
    )
    first_frame: str | None = Field(default=None, description="可选首帧输入。")
    last_frame: str | None = Field(default=None, description="可选尾帧输入；仅 `MiniMax-Hailuo-02` 首尾帧模式支持。")
    resolution: str | None = Field(
        default=None,
        description="目标分辨率。官方当前常见值为 `512P`、`768P`、`1080P`。",
        json_schema_extra={"enum": ["512P", "768P", "1080P"]},
    )
    aspect_ratio: str | None = Field(
        default=None,
        description="目标宽高比。官方当前常见值为 `16:9`、`9:16`、`1:1`。",
        json_schema_extra={"enum": ["16:9", "9:16", "1:1"]},
    )
    seconds: int | None = Field(
        default=None,
        description="目标时长，单位秒。MiniMax 官方当前常见取值为 `6`、`10`。",
        json_schema_extra={"enum": [6, 10]},
    )
    prompt_optimizer: bool | None = Field(
        default=None,
        description="是否启用官方提示词优化。",
    )
    fast_pretreatment: bool | None = Field(
        default=None,
        description="是否启用官方快速预处理。主要适用于 Fast 模型。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "电影感十足的雨夜街头，镜头缓慢推进到霓虹招牌前。",
                "input_reference": "https://example.com/frame.png",
                "resolution": "768P",
                "aspect_ratio": "16:9",
                "seconds": 6,
            }
        },
    )


class WanVideoRequest(OpenSchemaModel):
    prompt: str | None = Field(default=None, description="视频提示词。文生模式必填；图生和参考生模式可选。")
    input_reference: str | None = Field(
        default=None,
        description="可选单图输入，用于图生视频。",
    )
    reference_urls: list[str] | None = Field(
        default=None,
        description="可选参考素材列表，用于参考生视频。当前建议不超过 5 个 URL。",
    )
    audio_url: str | None = Field(
        default=None,
        description="可选参考音频 URL。当前主要用于有声视频生成。",
    )
    negative_prompt: str | None = Field(default=None, description="可选负向提示词。")
    size: str | None = Field(
        default=None,
        description="目标尺寸，优先级高于 `resolution + aspect_ratio`。常见值：`1280*720`、`720*1280`、`960*960`、`1920*1080`、`1080*1920`、`1440*1440`。",
    )
    resolution: str | None = Field(
        default=None,
        description="目标分辨率档位。当前平台支持 `720P`、`1080P`。",
        json_schema_extra={"enum": ["720P", "1080P"]},
    )
    aspect_ratio: str | None = Field(
        default=None,
        description="目标宽高比。当前平台支持 `16:9`、`9:16`、`1:1`。",
        json_schema_extra={"enum": ["16:9", "9:16", "1:1"]},
    )
    seconds: int | None = Field(
        default=None,
        description="目标时长，单位秒。Wan 2.6 不同模式支持范围不同，当前建议按官方常见区间填写。",
    )
    prompt_extend: bool | None = Field(default=None, description="是否启用官方提示词扩写。")
    generate_audio: bool | None = Field(
        default=None,
        description="是否生成音频。`wan2.6-flash` 的图生和参考生支持静音模式；标准 `wan2.6` 当前不开放静音。",
    )
    watermark: bool | None = Field(default=None, description="是否添加水印。")
    shot_type: str | None = Field(
        default=None,
        description="参考生视频的镜头类型控制。当前仅支持 `single`、`multi`。",
        json_schema_extra={"enum": ["single", "multi"]},
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "一段电影感十足的产品开箱镜头。",
                "input_reference": "https://example.com/product.png",
                "resolution": "720P",
                "aspect_ratio": "16:9",
                "seconds": 5,
            }
        },
    )


class KlingVideoRequest(OpenSchemaModel):
    prompt: str = Field(description="视频提示词。Kling O1 当前所有公开模式都要求提供提示词。")
    input_reference: str | None = Field(
        default=None,
        description="可选单图输入，用于单图视频生成。",
    )
    reference_images: list[str] | None = Field(
        default=None,
        description="可选参考图列表，用于多参考图视频生成。",
    )
    video_url: str | None = Field(
        default=None,
        description="可选参考视频 URL。当前公开入口按视频参考模式处理，不开放 base video 编辑模式。",
    )
    first_frame: str | None = Field(default=None, description="可选首帧输入。")
    last_frame: str | None = Field(default=None, description="可选尾帧输入，需与 `first_frame` 配合。")
    mode: str | None = Field(
        default=None,
        description="生成档位。官方当前支持 `std`、`pro`，默认按 `pro` 处理。",
        json_schema_extra={"enum": ["std", "pro"]},
    )
    aspect_ratio: str | None = Field(
        default=None,
        description="目标宽高比。官方当前支持 `16:9`、`9:16`、`1:1`。",
        json_schema_extra={"enum": ["16:9", "9:16", "1:1"]},
    )
    seconds: int | None = Field(
        default=None,
        description="目标时长，单位秒。Kling O1 当前公开支持 `5`、`10`。",
        json_schema_extra={"enum": [5, 10]},
    )
    watermark: bool | None = Field(default=None, description="是否同时生成带水印结果。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "让画面中的角色朝镜头挥手并缓慢向前走。",
                "input_reference": "https://example.com/frame.png",
                "mode": "pro",
                "aspect_ratio": "16:9",
                "seconds": 5,
            }
        },
    )


class ViduVideoRequest(OpenSchemaModel):
    mode: Literal["text", "image", "start_end"] = Field(
        description="Vidu 生成模式。`text` 对应文生视频，`image` 对应图生视频，`start_end` 对应首尾帧生视频。",
    )
    prompt: str | None = Field(default=None, description="文本提示词。文生模式必填；图生和首尾帧模式可选。")
    images: list[str] | None = Field(
        default=None,
        description="图像输入。图生模式必须传 1 张；首尾帧模式必须传 2 张；支持 URL 或 `data:image/...;base64,...`。",
    )
    duration: int | None = Field(default=None, description="视频时长。Q3 系列默认 `5`，当前支持 `1-16` 秒。")
    seed: int | None = Field(default=None, description="随机种子。不传或传 `0` 时由 Vidu 自动生成。")
    resolution: Literal["540p", "720p", "1080p"] | None = Field(
        default=None,
        description="目标分辨率。Q3 系列默认 `720p`。",
    )
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] | None = Field(
        default=None,
        description="宽高比。当前仅文生视频模式公开该参数。",
    )
    movement_amplitude: Literal["auto", "small", "medium", "large"] | None = Field(
        default=None,
        description="镜头动态幅度。Q2/Q3 系列当前可能忽略该参数。",
    )
    style: str | None = Field(
        default=None,
        description="Vidu 文生视频风格参数。当前主要见于文生模式，常见值如 `general`。",
    )
    bgm: bool | None = Field(
        default=None,
        description="是否添加背景音乐。Q3 系列当前不生效，但保留原生参数透传。",
    )
    audio: bool | None = Field(
        default=None,
        description="是否启用音视频直出。Q3 系列默认按 `true` 处理；传 `false` 时生成静音视频。",
    )
    audio_type: Literal["all", "speech_only", "sound_effect_only"] | None = Field(
        default=None,
        description="图生视频音频类型。文生和首尾帧模式当前不公开该参数。",
    )
    voice_id: str | None = Field(
        default=None,
        description="音色 ID。图生模式公开该参数；Q3 系列当前不生效，但保留原生参数透传。",
    )
    is_rec: bool | None = Field(
        default=None,
        description="是否启用推荐提示词。启用后每个任务额外消耗 `10` 积分。",
    )
    off_peak: bool | None = Field(
        default=None,
        description="是否使用错峰模式。Q3 系列仅在音视频直出开启时支持错峰。",
    )
    watermark: bool | None = Field(default=None, description="是否输出带水印的视频结果。")
    wm_position: Literal[1, 2, 3, 4] | None = Field(
        default=None,
        description="水印位置。`1` 左上、`2` 右上、`3` 右下、`4` 左下。",
    )
    wm_url: str | None = Field(default=None, description="自定义水印图片 URL。")
    meta_data: str | dict[str, Any] | None = Field(
        default=None,
        description="元数据标识。官方原生字段是 JSON 字符串；平台允许直接传对象并在上游前转成字符串。",
    )
    payload: str | None = Field(default=None, description="透传字段，Vidu 不做处理。")
    callback_url: str | None = Field(default=None, description="任务状态回调地址。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "mode": "image",
                "prompt": "让角色回头看向镜头，镜头缓慢推进。",
                "images": ["https://example.com/frame.png"],
                "duration": 5,
                "resolution": "720p",
                "audio": True,
                "off_peak": False,
                "watermark": True,
            }
        },
    )


class VideoTaskResponse(OpenSchemaModel):
    id: str | None = Field(default=None, description="平台任务 ID 或上游返回的视频 ID。")
    provider_task_id: str | None = Field(default=None, description="上游供应商任务 ID。")
    object: str | None = Field(default=None, description="响应对象类型，通常为 video。")
    created_at: int | None = Field(default=None, description="Unix 时间戳。")
    status: str | None = Field(default=None, description="任务状态，例如 submitted、processing、completed。")
    model: str | None = Field(default=None, description="实际命中的模型。")
    progress: int | None = Field(default=None, description="任务进度，0-100。")
    seconds: str | None = Field(default=None, description="目标视频时长。")
    size: str | None = Field(default=None, description="目标视频尺寸。")
    url: str | None = Field(default=None, description="视频下载地址。")
    error: Any = Field(default=None, description="任务错误信息。")
    video: dict[str, Any] | None = Field(default=None, description="视频对象。")
    thumbnail: dict[str, Any] | None = Field(default=None, description="缩略图对象。")
    spritesheet: dict[str, Any] | None = Field(default=None, description="雪碧图对象。")
    provider_raw: dict[str, Any] | None = Field(default=None, description="上游原始响应。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "id": "task_1234567890abcdef123456",
                "provider_task_id": "provider_123",
                "object": "video",
                "created_at": 1773571200,
                "status": "submitted",
                "model": "veo-3.1-fast",
                "progress": 0,
                "seconds": "8",
                "size": "1280x720",
                "url": None,
                "error": None,
            }
        },
    )
