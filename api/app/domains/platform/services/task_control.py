from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import User

ACTIVE_TASK_STATUSES = ("submitted", "queued", "processing")


class TaskControlService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_active_account(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None or user.status != "active":
            raise HTTPException(status_code=403, detail="account_not_active")
        return user

    def ensure_non_negative_available_balance(self, user_id: int) -> User:
        user = self.ensure_active_account(user_id)
        available = Decimal(user.balance)
        if available < 0:
            raise HTTPException(status_code=402, detail="insufficient_balance")
        return user

    def ensure_sufficient_available_balance(
        self,
        *,
        user_id: int,
        power_amount: Decimal,
    ) -> User:
        user = self.ensure_active_account(user_id)
        available = Decimal(user.balance)
        if available < Decimal(power_amount):
            raise HTTPException(status_code=402, detail="insufficient_balance")
        return user
