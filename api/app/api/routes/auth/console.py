from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.auth import UserAccessContext, require_user_access, require_user_session
from app.api.deps import get_db
from app.api.openapi_responses import SESSION_AUTH_ERROR_RESPONSES, USER_AUTH_ERROR_RESPONSES
from app.api.schemas import (
    ModelPricingItem,
    ProviderAccountCreateRequest,
    ProviderAccountProviderOptionResponse,
    ProviderAccountResponse,
    ProviderAccountUpdateRequest,
    UserApiKeyCreateRequest,
    UserApiKeyResponse,
    UserApiKeyUpdateRequest,
    UserGrowthContextResponse,
    UserGrowthContextUpsertRequest,
    UserLogDetailResponse,
    UserLogListResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserTaskDetailResponse,
    UserTaskListResponse,
)
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.public_model_pricing import PublicModelPricingService
from app.domains.platform.services.provider_accounts import ProviderAccountService
from app.domains.platform.services.user_console import UserConsoleService
from app.domains.platform.services.system_api_keys import SystemApiKeyService

router = APIRouter()


@router.get(
    "/v1/api-keys",
    summary="获取当前用户 API Key 列表",
    response_model=list[UserApiKeyResponse],
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_api_keys(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> list[dict]:
    return UserConsoleService(db).list_api_keys(user_id=ctx.user_id)


@router.post(
    "/v1/api-keys",
    status_code=status.HTTP_201_CREATED,
    summary="创建当前用户 API Key",
    response_model=UserApiKeyResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def create_api_key(
    payload: UserApiKeyCreateRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).create_api_key(user_id=ctx.user_id, key_name=payload.key_name)


@router.post(
    "/v1/api-keys/{api_key_id}/reveal",
    summary="查看当前用户 API Key 明文",
    response_model=UserApiKeyResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def reveal_api_key(
    api_key_id: int,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).reveal_api_key(user_id=ctx.user_id, api_key_id=api_key_id)


@router.get(
    "/v1/api-keys/system-default",
    summary="获取当前用户系统默认 API Key",
    response_model=UserApiKeyResponse,
    responses=SESSION_AUTH_ERROR_RESPONSES,
)
def get_system_default_api_key(
    ctx: UserAccessContext = Depends(require_user_session),
    db: Session = Depends(get_db),
) -> dict:
    return SystemApiKeyService(db).get_system_default_key_response(user_id=ctx.user_id)


@router.post(
    "/v1/api-keys/system-default/reset",
    summary="重置当前用户系统默认 API Key",
    response_model=UserApiKeyResponse,
    responses=SESSION_AUTH_ERROR_RESPONSES,
)
def reset_system_default_api_key(
    ctx: UserAccessContext = Depends(require_user_session),
    db: Session = Depends(get_db),
) -> dict:
    return SystemApiKeyService(db).reset_system_default_key(user_id=ctx.user_id)


@router.patch(
    "/v1/api-keys/{api_key_id}",
    summary="更新当前用户 API Key",
    response_model=UserApiKeyResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def update_api_key(
    api_key_id: int,
    payload: UserApiKeyUpdateRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).update_api_key(
        user_id=ctx.user_id,
        api_key_id=api_key_id,
        key_name=payload.key_name,
        status=payload.status,
    )


@router.delete(
    "/v1/api-keys/{api_key_id}",
    summary="删除当前用户 API Key",
    response_model=UserApiKeyResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def delete_api_key(
    api_key_id: int,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).delete_api_key(
        user_id=ctx.user_id,
        api_key_id=api_key_id,
    )


@router.get(
    "/v1/profile",
    summary="获取当前用户资料",
    response_model=UserProfileResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def get_profile(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).get_profile(user_id=ctx.user_id)


@router.post(
    "/v1/growth-context",
    summary="同步当前用户归因快照",
    response_model=UserGrowthContextResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def sync_growth_context(
    payload: UserGrowthContextUpsertRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    service = BusinessTrackingService(db)
    service.sync_growth_context(
        user_id=ctx.user_id,
        growth_context=payload.growth_context.model_dump(exclude_none=True),
    )
    db.commit()
    return service.serialize_growth_context(user_id=ctx.user_id)


@router.get(
    "/v1/model-pricing",
    summary="获取对外开放模型价格列表",
    response_model=list[ModelPricingItem],
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_model_pricing(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> list[dict]:
    del ctx
    return PublicModelPricingService(db).list_models()


@router.patch(
    "/v1/profile",
    summary="更新当前用户资料",
    response_model=UserProfileResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def update_profile(
    payload: UserProfileUpdateRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).update_profile(user_id=ctx.user_id, name=payload.name)


@router.get(
    "/v1/async-tasks",
    summary="获取当前用户异步任务列表",
    response_model=UserTaskListResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_async_tasks(
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    model: str | None = Query(default=None),
    query: str | None = Query(default=None),
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    total, summary, items = UserConsoleService(db).list_tasks_paginated(
        user_id=ctx.user_id,
        page=page,
        size=size,
        status=status,
        model=model,
        query=query,
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "summary": summary,
        "items": items,
    }


@router.get(
    "/v1/async-tasks/{task_id}",
    summary="获取当前用户异步任务详情",
    response_model=UserTaskDetailResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def get_async_task_detail(
    task_id: str,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).get_task_detail(user_id=ctx.user_id, task_id=task_id)


@router.get(
    "/v1/logs",
    summary="获取当前用户调用日志",
    response_model=UserLogListResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_logs(
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    model: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    total, items = UserConsoleService(db).list_logs_paginated(
        user_id=ctx.user_id,
        page=page,
        size=size,
        status=status,
        model=model,
        request_id=request_id,
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items,
    }


@router.get(
    "/v1/logs/{request_id}",
    summary="获取当前用户单条调用日志详情",
    response_model=UserLogDetailResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def get_log_detail(
    request_id: str,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return UserConsoleService(db).get_log_detail(user_id=ctx.user_id, request_id=request_id)


@router.get(
    "/v1/provider-accounts/providers",
    summary="获取供应商账号可选供应商列表",
    response_model=list[ProviderAccountProviderOptionResponse],
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_provider_account_providers(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> list[dict]:
    del ctx
    return ProviderAccountService(db).list_provider_options()


@router.get(
    "/v1/provider-accounts",
    summary="获取当前用户供应商账号列表",
    response_model=list[ProviderAccountResponse],
    responses=USER_AUTH_ERROR_RESPONSES,
)
def list_provider_accounts(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> list[dict]:
    return ProviderAccountService(db).list_user_accounts(user_id=ctx.user_id)


@router.post(
    "/v1/provider-accounts",
    status_code=status.HTTP_201_CREATED,
    summary="创建当前用户供应商账号",
    response_model=ProviderAccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def create_provider_account(
    payload: ProviderAccountCreateRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return ProviderAccountService(db).create_user_account(user_id=ctx.user_id, payload=payload.model_dump())


@router.patch(
    "/v1/provider-accounts/{account_id}",
    summary="更新当前用户供应商账号",
    response_model=ProviderAccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def update_provider_account(
    account_id: int,
    payload: ProviderAccountUpdateRequest,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return ProviderAccountService(db).update_user_account(
        user_id=ctx.user_id,
        account_id=account_id,
        payload=payload.model_dump(exclude_unset=True),
    )


@router.delete(
    "/v1/provider-accounts/{account_id}",
    summary="删除当前用户供应商账号",
    response_model=ProviderAccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def delete_provider_account(
    account_id: int,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return ProviderAccountService(db).delete_user_account(user_id=ctx.user_id, account_id=account_id)


@router.post(
    "/v1/provider-accounts/{account_id}/verify",
    summary="验证当前用户供应商账号",
    response_model=ProviderAccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def verify_provider_account(
    account_id: int,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return ProviderAccountService(db).verify_user_account(user_id=ctx.user_id, account_id=account_id)


@router.post(
    "/v1/provider-accounts/{account_id}/sync-balance",
    summary="同步当前用户供应商账号余额",
    response_model=ProviderAccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def sync_provider_account_balance(
    account_id: int,
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    return ProviderAccountService(db).sync_balance_user_account(user_id=ctx.user_id, account_id=account_id)
