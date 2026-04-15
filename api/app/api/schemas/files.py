from __future__ import annotations

from pydantic import ConfigDict, Field

from app.api.schemas.common import OpenSchemaModel


class FileUploadPolicyRequest(OpenSchemaModel):
    filename: str = Field(description="原始文件名。")
    content_type: str = Field(description="文件 MIME 类型，例如 `image/png`、`video/mp4` 或 `audio/wav`。")
    size: int | None = Field(default=None, description="文件大小，单位字节。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "filename": "voice-sample.wav",
                "content_type": "audio/wav",
                "size": 524288,
            }
        },
    )


class FileImportUrlRequest(OpenSchemaModel):
    url: str = Field(description="要导入的远程文件 URL，仅支持 `http` 或 `https`。")
    filename: str | None = Field(default=None, description="可选。覆盖远程文件名。")
    content_type: str | None = Field(
        default=None,
        description="可选。覆盖远程响应的 MIME 类型，例如 `image/png`。",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "url": "https://example.com/assets/voice-sample.wav",
                "filename": "voice-sample.wav",
                "content_type": "audio/wav",
            }
        },
    )


class FileUploadPolicyResponse(OpenSchemaModel):
    file_id: str
    bucket: str
    endpoint: str
    object_key: str
    upload_url: str
    policy: str
    signature: str
    access_key_id: str
    expire_at: str
    max_size: int
    allowed_content_types: list[str]
    success_action_status: str


class FileCompleteRequest(OpenSchemaModel):
    file_id: str = Field(description="上传凭证返回的文件 ID。")
    size: int = Field(description="文件大小，单位字节。")
    content_type: str = Field(description="文件 MIME 类型。")
    etag: str | None = Field(default=None, description="对象存储返回的 ETag，可选。")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "file_id": "file_a1b2c3d4e5f6",
                "size": 524288,
                "content_type": "audio/wav",
            }
        },
    )


class FileObjectResponse(OpenSchemaModel):
    file_id: str
    filename: str
    content_type: str | None = None
    size: int | None = None
    kind: str
    status: str
    bucket: str
    object_key: str
    url: str | None = None
    etag: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class FileListResponse(OpenSchemaModel):
    total: int
    page: int
    size: int
    items: list[FileObjectResponse]
