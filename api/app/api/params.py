from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Header, Query


MetricsWindowValue = Literal["1h", "24h", "7d"]


ChainHeader = Annotated[
    str | None,
    Header(
        alias="X-API35-Chain",
        description=(
            "按逗号分隔的供应商代码列表。"
            "例如 `google_veo3,minimax_official`。"
            "不传时，平台会按默认链顺序选择供应商。"
            "传入后只会在这条链内按顺序尝试，不会再追加链外供应商。"
        ),
    ),
]

FallbackHeader = Annotated[
    bool | None,
    Header(
        alias="X-API35-Fallback",
        description=(
            "默认链模式下，首位供应商失败时是否继续尝试后续供应商。"
            "可选值：`true`、`false`。"
            "不传时默认按 `true` 处理。"
            "传了 `X-API35-Chain` 时，回退顺序由链本身决定。"
        ),
    ),
]

MetricsWindowHeader = Annotated[
    MetricsWindowValue | None,
    Header(
        alias="X-API35-Metrics-Window",
        description=(
            "供应商成功率和耗时统计窗口。"
            "可选值：`1h`、`24h`、`7d`。"
            "不传时默认使用 `24h`。"
        ),
    ),
]

MetricsWindowQuery = Annotated[
    MetricsWindowValue,
    Query(
        description=(
            "供应商成功率和耗时统计窗口。"
            "可选值：`1h`、`24h`、`7d`。"
        ),
    ),
]
