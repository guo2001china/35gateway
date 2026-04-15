from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import RechargeOrder, RedemptionCode, User, UserAuthIdentity
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.recharge import POWER_QUANTIZE, RechargeService

CODE_ALPHABET = string.ascii_uppercase + string.digits


class RedemptionCodeService:
    def __init__(self, db: Session):
        self.db = db

    def list_codes(
        self,
        *,
        page: int = 1,
        size: int = 20,
        code: str | None = None,
        channel: str | None = None,
        status_code: str | None = None,
    ) -> tuple[int, list[RedemptionCode]]:
        query = self.db.query(RedemptionCode)

        normalized_code = self.normalize_code(code) if code else None
        if normalized_code:
            query = query.filter(RedemptionCode.code.ilike(f"%{normalized_code}%"))

        normalized_channel = (channel or "").strip()
        if normalized_channel:
            query = query.filter(RedemptionCode.channel == normalized_channel)

        normalized_status = (status_code or "").strip().lower()
        if normalized_status:
            query = query.filter(RedemptionCode.status == normalized_status)

        total = query.count()
        rows = query.order_by(RedemptionCode.id.desc()).offset((page - 1) * size).limit(size).all()
        return total, rows

    def batch_create(
        self,
        *,
        channel: str,
        quantity: int,
        power_amount: Decimal,
    ) -> list[RedemptionCode]:
        normalized_channel = (channel or "").strip()
        if not normalized_channel:
            raise HTTPException(status_code=422, detail="invalid_redemption_channel")
        if quantity < 1 or quantity > 500:
            raise HTTPException(status_code=422, detail="invalid_redemption_quantity")

        normalized_power_amount = Decimal(str(power_amount)).quantize(POWER_QUANTIZE, rounding=ROUND_DOWN)
        if normalized_power_amount <= 0:
            raise HTTPException(status_code=422, detail="invalid_redemption_power_amount")

        codes = self._generate_unique_codes(quantity)
        rows = [
            RedemptionCode(
                code=code_value,
                power_amount=normalized_power_amount,
                channel=normalized_channel,
                status="unused",
            )
            for code_value in codes
        ]
        self.db.add_all(rows)
        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        return rows

    def delete_unused(self, *, code_id: int) -> RedemptionCode:
        row = self.db.query(RedemptionCode).filter(RedemptionCode.id == code_id).with_for_update().first()
        if row is None:
            raise HTTPException(status_code=404, detail="redemption_code_not_found")
        if row.status != "unused":
            raise HTTPException(status_code=409, detail="redemption_code_not_deletable")

        self.db.delete(row)
        self.db.commit()
        return row

    def redeem(self, *, user_id: int, code: str) -> tuple[RedemptionCode, RechargeOrder, User]:
        normalized_code = self.normalize_code(code)
        if not normalized_code:
            raise HTTPException(status_code=422, detail="invalid_redemption_code")

        redemption = (
            self.db.query(RedemptionCode)
            .filter(RedemptionCode.code == normalized_code)
            .with_for_update()
            .first()
        )
        if redemption is None:
            raise HTTPException(status_code=404, detail="redemption_code_not_found")
        if redemption.status == "used":
            raise HTTPException(status_code=409, detail="redemption_code_already_used")
        if redemption.status == "expired":
            raise HTTPException(status_code=409, detail="redemption_code_expired")
        if redemption.status != "unused":
            raise HTTPException(status_code=409, detail="redemption_code_invalid_status")

        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if user is None or user.status != "active":
            raise HTTPException(status_code=403, detail="account_not_active")

        power_amount = Decimal(str(redemption.power_amount or "0")).quantize(POWER_QUANTIZE, rounding=ROUND_DOWN)
        if power_amount <= 0:
            raise HTTPException(status_code=409, detail="invalid_redemption_power_amount")

        identity = (
            self.db.query(UserAuthIdentity)
            .filter(UserAuthIdentity.user_id == user.id, UserAuthIdentity.phone.isnot(None))
            .order_by(UserAuthIdentity.id.desc())
            .first()
        )
        balance_before = Decimal(str(user.balance or "0"))
        balance_after = (balance_before + power_amount).quantize(POWER_QUANTIZE, rounding=ROUND_DOWN)
        now = datetime.now(timezone.utc)

        user.balance = balance_after
        redemption.status = "used"
        redemption.redeemed_user_id = user.id
        redemption.redeemed_user_no = user.user_no
        redemption.redeemed_name = user.name
        redemption.redeemed_phone = identity.phone if identity is not None else None
        redemption.redeemed_at = now

        recharge_order = RechargeOrder(
            recharge_order_no=RechargeService.new_recharge_order_no(),
            user_id=user.id,
            channel="redeem_code",
            amount=Decimal("0").quantize(POWER_QUANTIZE, rounding=ROUND_DOWN),
            currency="CNY",
            power_rate=None,
            power_amount=power_amount,
            status="paid",
        )

        self.db.add(user)
        self.db.add(redemption)
        self.db.add(recharge_order)
        BusinessTrackingService(self.db).record_event(
            user_id=user.id,
            event_name="redemption_code_redeemed",
            power_amount=power_amount,
            currency="CNY",
            context_payload={
                "redemption_code_id": redemption.id,
                "redemption_channel": redemption.channel,
                "recharge_order_no": recharge_order.recharge_order_no,
            },
            occurred_at=now,
        )
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(redemption)
        self.db.refresh(recharge_order)
        return redemption, recharge_order, user

    @staticmethod
    def normalize_code(code: str | None) -> str:
        return (code or "").strip().upper()

    @staticmethod
    def _new_code(length: int = 16) -> str:
        return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))

    def _generate_unique_codes(self, quantity: int) -> list[str]:
        codes: list[str] = []
        seen: set[str] = set()
        attempts = 0
        while len(codes) < quantity and attempts < 12:
            need = quantity - len(codes)
            batch: list[str] = []
            while len(batch) < need * 2:
                candidate = self._new_code()
                if candidate in seen:
                    continue
                seen.add(candidate)
                batch.append(candidate)

            existing_rows = self.db.query(RedemptionCode.code).filter(RedemptionCode.code.in_(batch)).all()
            existing = {row[0] for row in existing_rows}
            for candidate in batch:
                if candidate in existing:
                    continue
                codes.append(candidate)
                if len(codes) >= quantity:
                    break
            attempts += 1

        if len(codes) < quantity:
            raise HTTPException(status_code=500, detail="redemption_code_generation_failed")
        return codes[:quantity]
