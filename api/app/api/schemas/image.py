from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from app.api.schemas.common import OpenSchemaModel


class BananaRequest(OpenSchemaModel):
    prompt: str = Field(
        description="图片生成或编辑提示词。官网公开契约以 Google 官方 Nano Banana 参数为准，其他供应商按同一契约适配。"
    )
    image_urls: list[str] | None = Field(
        default=None,
        description="可选公开图片 URL 列表。传入后按图片编辑模式处理。各供应商支持的参考图张数可能不同，超出能力时按供应商上限处理。",
    )
    aspect_ratio: str | None = Field(
        default=None,
        description=(
            "可选输出宽高比。Nano Banana / Nano Banana Pro 常见值：`1:1`、`2:3`、`3:2`、`3:4`、`4:3`、`4:5`、`5:4`、`9:16`、`16:9`、`21:9`；"
            "Nano Banana 2 额外支持 `1:4`、`1:8`、`4:1`、`8:1`。若回退到非 Google 官方供应商，少数比例可能按供应商能力降级或忽略。"
        ),
        json_schema_extra={"enum": ["1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1", "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9"]},
    )
    resolution: str | None = Field(
        default=None,
        description=(
            "可选输出分辨率。Nano Banana 固定为 1K，一般无需传；Nano Banana Pro 支持 `1K`、`2K`、`4K`；"
            "Nano Banana 2 额外支持 `512`（0.5K）。Google 官方完整支持该分辨率矩阵，其他供应商不支持时会按自身能力处理。"
        ),
        json_schema_extra={"enum": ["512", "1K", "2K", "4K"]},
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "把这张产品图改成干净的广告主视觉。",
                "image_urls": ["https://example.com/input-product.png"],
                "aspect_ratio": "16:9",
                "resolution": "2K",
            }
        },
    )


class SeedreamBaseRequest(OpenSchemaModel):
    prompt: str = Field(description="图片生成提示词。")
    image: str | list[str] | None = Field(
        default=None,
        description="可选参考图 URL 或 Base64。传入后按图生模式处理。",
    )
    size: str | None = Field(
        default=None,
        description="官方图片尺寸参数，例如 `1024x1024`、`2048x2048` 或其他火山引擎支持值。",
    )
    response_format: str | None = Field(
        default="url",
        description="返回格式。常见值：`url`、`b64_json`。默认 `url`。",
        json_schema_extra={"enum": ["url", "b64_json"]},
    )
    stream: bool | None = Field(
        default=None,
        description="是否启用流式返回。当前平台统一返回最终结果。",
    )
    watermark: bool | None = Field(
        default=None,
        description="是否添加水印。",
    )


class SeedreamRequest(SeedreamBaseRequest):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "一张极简风格的香水产品海报，白底，柔和棚拍光。",
                "image": "https://example.com/input.png",
                "size": "2048x2048",
                "response_format": "url",
                "watermark": False,
            }
        },
    )


class SeedreamLiteRequest(SeedreamBaseRequest):
    output_format: str | None = Field(
        default=None,
        description="可选输出图片格式。Doubao Seedream 5.0 Lite 官方支持 `jpeg`、`png`。",
        json_schema_extra={"enum": ["jpeg", "png"]},
    )
    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="官方工具参数数组；不同版本支持能力可能不同，当前平台按上游原样透传。",
    )
    sequential_image_generation: str | None = Field(
        default=None,
        description="可选串行生图模式；当前平台按上游原样透传。",
    )
    sequential_image_generation_options: dict[str, Any] | None = Field(
        default=None,
        description="串行生图配置项；当前平台按上游原样透传。",
    )
    optimize_prompt_options: dict[str, Any] | None = Field(
        default=None,
        description="Prompt 优化配置项；当前平台按上游原样透传。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "一张极简风格的香水产品海报，白底，柔和棚拍光。",
                "image": "https://example.com/input.png",
                "size": "2048x2048",
                "response_format": "url",
                "watermark": False,
                "output_format": "png",
            }
        },
    )


class ImageItem(OpenSchemaModel):
    url: str | None = Field(default=None, description="图片下载地址。")
    b64_json: str | None = Field(default=None, description="Base64 编码图片内容。")
    mime_type: str | None = Field(default=None, description="图片 MIME 类型。")
    width: int | None = Field(default=None, description="图片宽度。")
    height: int | None = Field(default=None, description="图片高度。")
    content_type: str | None = Field(default=None, description="图片内容类型。")


class ImageGenerationResponse(OpenSchemaModel):
    object: str | None = Field(default=None, description="响应对象类型，通常为 image_generation。")
    created_at: int | None = Field(default=None, description="Unix 时间戳。")
    model: str | None = Field(default=None, description="实际命中的模型。")
    images: list[ImageItem] = Field(default_factory=list, description="生成结果图片列表。")
    description: str | None = Field(default=None, description="模型返回的补充说明文本。")
    provider_raw: dict[str, Any] | None = Field(default=None, description="上游原始响应。")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "object": "image_generation",
                "created_at": 1773571200,
                "model": "nano-banana-pro",
                "images": [
                    {
                        "url": "https://example.com/output.png",
                        "width": 1024,
                        "height": 1024,
                        "content_type": "image/png",
                    }
                ],
                "description": "已生成一张商品广告图。",
            }
        },
    )
