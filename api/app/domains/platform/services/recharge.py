from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import User

POWER_QUANTIZE = Decimal("0.000001")


class RechargeService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def new_recharge_order_no() -> str:
        return f"rch_{uuid.uuid4().hex[:24]}"

    def get_account(self, *, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None or user.status != "active":
            raise HTTPException(status_code=403, detail="account_not_active")
        return user
