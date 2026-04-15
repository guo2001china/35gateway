from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OpenSchemaModel(BaseModel):
    """OpenAPI 基础模型：显式展示已知字段，同时允许额外字段透传。"""

    model_config = ConfigDict(extra="allow")


class ErrorResponse(BaseModel):
    detail: str = Field(description="稳定错误码，便于前端、联调和运营排查。")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "insufficient_balance",
            }
        }
    )
