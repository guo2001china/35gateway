from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import UserAccessContext, require_user_access
from app.api.deps import get_db
from app.api.openapi_responses import FILE_UPLOAD_ERROR_RESPONSES, USER_AUTH_ERROR_RESPONSES
from app.api.schemas import (
    FileCompleteRequest,
    FileImportUrlRequest,
    FileListResponse,
    FileObjectResponse,
    FileUploadPolicyRequest,
    FileUploadPolicyResponse,
)
from app.domains.platform.services.files import FileService

router = APIRouter()


@router.post(
    "/v1/files/upload",
    status_code=status.HTTP_201_CREATED,
    summary="直接上传文件",
    response_model=FileObjectResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
async def upload_file(
    file: UploadFile = File(description="要上传的图片、视频或音频文件。"),
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """通过后端中转上传文件，便于在 API 文档页直接调试。"""
    if not file.filename:
        raise HTTPException(status_code=422, detail="missing_filename")
    if not file.content_type:
        raise HTTPException(status_code=422, detail="missing_content_type")
    content = await file.read()
    return FileService(db).upload_file(
        user_id=ctx.user_id,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
    )


@router.post(
    "/v1/files/import-url",
    status_code=status.HTTP_201_CREATED,
    summary="通过 URL 导入文件",
    response_model=FileObjectResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
def import_file_from_url(
    payload: FileImportUrlRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """下载远程文件后上传到 OSS，并登记为当前用户文件。"""
    return FileService(db).import_file_from_url(
        user_id=ctx.user_id,
        url=payload.url,
        filename=payload.filename,
        content_type=payload.content_type,
    )


@router.post(
    "/v1/files/upload-policy",
    status_code=status.HTTP_201_CREATED,
    summary="获取 OSS 上传凭证",
    response_model=FileUploadPolicyResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
def create_upload_policy(
    payload: FileUploadPolicyRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """为当前用户签发阿里云 OSS 直传凭证。"""
    return FileService(db).create_upload_policy(
        user_id=ctx.user_id,
        filename=payload.filename,
        content_type=payload.content_type,
        size=payload.size,
    )


@router.post(
    "/v1/files/complete",
    summary="确认文件上传完成",
    response_model=FileObjectResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
def complete_upload(
    payload: FileCompleteRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """在前端直传成功后登记文件完成状态。"""
    return FileService(db).complete_upload(
        user_id=ctx.user_id,
        file_id=payload.file_id,
        size=payload.size,
        content_type=payload.content_type,
        etag=payload.etag,
    )


@router.get(
    "/v1/files",
    summary="获取文件列表",
    response_model=FileListResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
def list_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    kind: str | None = Query(default=None),
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """返回当前用户上传文件列表。"""
    total, items = FileService(db).list_files(
        user_id=ctx.user_id,
        page=page,
        size=size,
        kind=kind,
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items,
    }


@router.get(
    "/v1/files/{file_id}",
    summary="获取文件详情",
    response_model=FileObjectResponse,
    responses={**USER_AUTH_ERROR_RESPONSES, **FILE_UPLOAD_ERROR_RESPONSES},
)
def get_file(
    file_id: str,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """返回当前用户单个文件详情和临时访问 URL。"""
    return FileService(db).get_file(user_id=ctx.user_id, file_id=file_id)
