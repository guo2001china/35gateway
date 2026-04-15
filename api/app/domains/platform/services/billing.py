from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import BillingRecord, User
from app.domains.platform.services.business_tracking import BusinessTrackingService
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def record_sync_success(
        self,
        *,
        request_id: int,
        user_id: int,
        api_key_id: int,
        provider_code: str,
        provider_account_id: int | None,
        provider_account_short_id: str | None,
        provider_account_owner_type: str | None,
        public_model_code: str,
        route_group: str,
        billing_unit: str,
        billing_snapshot: dict[str, Any],
    ) -> BillingRecord:
        power_amount = self._extract_power_amount(billing_snapshot)
        sale_amount = self._extract_decimal_field(billing_snapshot, "sale_amount")
        cost_amount = self._extract_decimal_field(billing_snapshot, "cost_amount")
        margin_amount = self._extract_decimal_field(billing_snapshot, "margin_amount")
        record = BillingRecord(
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            provider_code=provider_code,
            provider_account_id=provider_account_id,
            provider_account_short_id=provider_account_short_id,
            provider_account_owner_type=provider_account_owner_type,
            public_model_code=public_model_code,
            route_group=route_group,
            billing_mode="final",
            billing_unit=billing_unit,
            billing_snapshot=billing_snapshot,
            sale_amount=sale_amount,
            sale_currency=self._extract_string_field(billing_snapshot, "sale_currency"),
            cost_amount=cost_amount,
            cost_currency=self._extract_string_field(billing_snapshot, "cost_currency"),
            margin_amount=margin_amount,
            power_amount=power_amount,
            status="succeeded",
        )
        self.db.add(record)
        self.db.flush()
        self._record_business_event(record, event_name="billing_succeeded")
        if power_amount is not None and power_amount > 0:
            self._apply_account_charge(
                user_id=user_id,
                power_amount=power_amount,
                reference_type="billing_record",
                reference_id=str(record.id),
            )
        self.db.commit()
        self.db.refresh(record)
        return record

    def record_async_pending(
        self,
        *,
        request_id: int,
        user_id: int,
        api_key_id: int,
        provider_code: str,
        provider_account_id: int | None,
        provider_account_short_id: str | None,
        provider_account_owner_type: str | None,
        public_model_code: str,
        route_group: str,
        billing_unit: str,
        billing_snapshot: dict[str, Any],
    ) -> BillingRecord:
        power_amount = self._extract_power_amount(billing_snapshot)
        sale_amount = self._extract_decimal_field(billing_snapshot, "sale_amount")
        cost_amount = self._extract_decimal_field(billing_snapshot, "cost_amount")
        margin_amount = self._extract_decimal_field(billing_snapshot, "margin_amount")
        record = BillingRecord(
            request_id=request_id,
            user_id=user_id,
            api_key_id=api_key_id,
            provider_code=provider_code,
            provider_account_id=provider_account_id,
            provider_account_short_id=provider_account_short_id,
            provider_account_owner_type=provider_account_owner_type,
            public_model_code=public_model_code,
            route_group=route_group,
            billing_mode="final",
            billing_unit=billing_unit,
            billing_snapshot=billing_snapshot,
            sale_amount=sale_amount,
            sale_currency=self._extract_string_field(billing_snapshot, "sale_currency"),
            cost_amount=cost_amount,
            cost_currency=self._extract_string_field(billing_snapshot, "cost_currency"),
            margin_amount=margin_amount,
            power_amount=power_amount,
            status="pending",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def finalize_async(
        self,
        *,
        request_id: int,
        final_status: str,
        billing_snapshot: dict[str, Any] | None = None,
    ) -> BillingRecord | None:
        record = (
            self.db.query(BillingRecord)
            .filter(BillingRecord.request_id == request_id)
            .order_by(BillingRecord.id.desc())
            .first()
        )
        if record is None:
            return None

        previous_status = record.status
        record.status = final_status
        if billing_snapshot:
            merged_snapshot = dict(record.billing_snapshot or {})
            merged_snapshot.update(billing_snapshot)
            record.billing_snapshot = merged_snapshot
        current_snapshot = dict(record.billing_snapshot or {})
        record.sale_amount = self._extract_decimal_field(current_snapshot, "sale_amount")
        record.sale_currency = self._extract_string_field(current_snapshot, "sale_currency")
        record.cost_amount = self._extract_decimal_field(current_snapshot, "cost_amount")
        record.cost_currency = self._extract_string_field(current_snapshot, "cost_currency")
        record.margin_amount = self._extract_decimal_field(current_snapshot, "margin_amount")
        record.power_amount = self._extract_power_amount(current_snapshot)
        self.db.add(record)

        if final_status == "succeeded" and record.power_amount is not None and record.power_amount > 0:
            power_amount = record.power_amount
            self._apply_account_charge(
                user_id=record.user_id,
                power_amount=power_amount,
                reference_type="billing_record",
                reference_id=str(record.id),
            )
        if previous_status != final_status:
            if final_status == "succeeded":
                self._record_business_event(record, event_name="billing_succeeded")
            elif final_status == "waived":
                self._record_business_event(record, event_name="billing_waived")

        self.db.commit()
        self.db.refresh(record)
        return record

    def _apply_account_charge(
        self,
        *,
        user_id: int,
        power_amount: Decimal,
        reference_type: str,
        reference_id: str,
    ) -> None:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None:
            return
        balance_before = Decimal(user.balance)
        charge_amount = Decimal(power_amount)

        balance_after = balance_before - charge_amount
        user.balance = balance_after
        self.db.add(user)

    def _extract_power_amount(self, snapshot: dict[str, Any] | None) -> Decimal | None:
        if not snapshot:
            return None
        power_amount = snapshot.get("power_amount")
        if power_amount is None:
            return None
        return Decimal(str(power_amount))

    def _extract_decimal_field(self, snapshot: dict[str, Any] | None, field: str) -> Decimal | None:
        if not snapshot:
            return None
        value = snapshot.get(field)
        if value is None:
            return None
        return Decimal(str(value))

    def _extract_string_field(self, snapshot: dict[str, Any] | None, field: str) -> str | None:
        if not snapshot:
            return None
        value = snapshot.get(field)
        if value is None:
            return None
        return str(value)

    def _record_business_event(self, record: BillingRecord, *, event_name: str) -> None:
        public_model_code = get_platform_config_snapshot().resolve_public_model_code(
            route_group=record.route_group,
            model_code=record.public_model_code,
        )
        BusinessTrackingService(self.db).record_event(
            user_id=record.user_id,
            event_name=event_name,
            public_model_code=public_model_code or record.public_model_code,
            route_group=record.route_group,
            provider_code=record.provider_code,
            amount=record.sale_amount,
            cost_amount=record.cost_amount,
            power_amount=record.power_amount,
            currency=record.sale_currency or record.cost_currency,
            context_payload={
                "billing_record_id": record.id,
                "status": record.status,
                "billing_unit": record.billing_unit,
            },
        )
