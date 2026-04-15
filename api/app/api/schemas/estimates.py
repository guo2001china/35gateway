from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from app.api.schemas.common import OpenSchemaModel


class EstimateRequest(OpenSchemaModel):
    model: str = Field(description="平台公开模型码，例如 `gpt-5.4`、`veo-3.1-fast` 或 `qwen3-tts-flash`。")
    payload: dict[str, Any] = Field(
        description="对应公开创建接口的请求体内容，不需要重复传 `model` 字段。",
    )
    chain: list[str] | None = Field(
        default=None,
        description="可选执行链，按顺序尝试；不传时由平台默认链决定。",
    )
    fallback: bool | None = Field(
        default=None,
        description="默认链模式下首位供应商失败时是否回退到后续供应商；默认按 `true` 处理。",
    )
    metrics_window: Literal["1h", "24h", "7d"] | None = Field(
        default=None,
        description="供应商成功率和耗时统计窗口；不传时默认使用 `24h`。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "model": "gpt-5.4",
                "payload": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "用一句话介绍 35m.ai 的 API 预计费接口。",
                        }
                    ]
                },
                "metrics_window": "24h",
            }
        },
    )


class EstimateBalanceSummary(OpenSchemaModel):
    available_amount: str
    enough_for_highest: bool


class EstimateSummaryResponse(OpenSchemaModel):
    model: str
    quote_mode: Literal["exact", "estimated"]
    route_mode: Literal["default", "chain"]
    lowest_price: str
    highest_price: str
    currency: str
    balance: EstimateBalanceSummary
    request_factors: dict[str, Any]

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "model": "veo-3-fast",
                "quote_mode": "exact",
                "route_mode": "default",
                "lowest_price": "4.6668",
                "highest_price": "7.7780",
                "currency": "CNY",
                "balance": {
                    "available_amount": "1000000.000000",
                    "enough_for_highest": True,
                },
                "request_factors": {
                    "seconds": 4,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                    "input_mode": "text",
                    "generate_audio": False,
                },
            }
        },
    )
