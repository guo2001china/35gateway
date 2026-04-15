from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import UserAccessContext, require_user_session
from app.api.deps import get_db
from app.api.openapi_responses import SESSION_AUTH_ERROR_RESPONSES
from app.domains.platform.services.redemption_codes import RedemptionCodeService

router = APIRouter()


class RedeemRedemptionCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class RedeemRedemptionCodeResponse(BaseModel):
    recharge_order_no: str
    balance_added: str
    balance: str


@router.post(
    "/v1/redemption-codes/redeem",
    summary="兑换兑换码",
    response_model=RedeemRedemptionCodeResponse,
    responses=SESSION_AUTH_ERROR_RESPONSES,
)
def redeem_redemption_code(
    payload: RedeemRedemptionCodeRequest,
    ctx: UserAccessContext = Depends(require_user_session),
    db: Session = Depends(get_db),
) -> dict:
    redemption, recharge_order, user = RedemptionCodeService(db).redeem(user_id=ctx.user_id, code=payload.code)
    return {
        "recharge_order_no": recharge_order.recharge_order_no,
        "balance_added": str(redemption.power_amount),
        "balance": str(user.balance),
    }
