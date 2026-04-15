from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import UserAccessContext, require_user_access
from app.api.deps import get_db
from app.api.openapi_responses import USER_AUTH_ERROR_RESPONSES
from app.api.schemas import (
    AccountResponse,
    UserContextResponse,
)
from app.domains.platform.services.recharge import RechargeService

router = APIRouter()


def _serialize_account(user_id: int, account) -> dict:
    # 用户余额现已直接收口到 users.balance，对外只暴露算力余额和状态。
    return {
        "user_id": user_id,
        "balance": str(account.balance),
        "status": account.status,
    }


@router.get(
    "/me",
    summary="获取当前用户上下文",
    response_model=UserContextResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def get_me(ctx: UserAccessContext = Depends(require_user_access)) -> dict:
    """返回当前认证用户的 user_id 和当前凭证类型。"""
    return {
        "user_id": ctx.user_id,
        "api_key_id": ctx.api_key_id,
        "auth_mode": ctx.auth_mode,
    }


@router.get(
    "/v1/account",
    summary="获取当前账户",
    response_model=AccountResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def get_account(
    ctx: UserAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> dict:
    """返回当前用户的算力账户快照。"""
    account = RechargeService(db).get_account(user_id=ctx.user_id)
    return _serialize_account(ctx.user_id, account)
