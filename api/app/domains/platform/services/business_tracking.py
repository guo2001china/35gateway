from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domains.platform.entities.entities import BusinessEvent, UserGrowthProfile

_DIRECT_LIKE_VALUES = {"", "direct", "(direct)", "none", "null", "unknown", "unset"}


class BusinessTrackingService:
    def __init__(self, db: Session):
        self.db = db

    def sync_growth_context(
        self,
        *,
        user_id: int,
        growth_context: dict[str, Any] | None,
        customer_motion: str = "self_serve",
    ) -> UserGrowthProfile:
        profile = self._get_or_create_profile(user_id)
        normalized = self._normalize_growth_context(growth_context)

        if customer_motion and not profile.customer_motion:
            profile.customer_motion = customer_motion

        if normalized:
            if not profile.first_touch_source and self._has_any_source(normalized):
                profile.first_touch_source = normalized.get("first_touch_source")
                profile.first_touch_medium = normalized.get("first_touch_medium")
                profile.first_touch_campaign = normalized.get("first_touch_campaign")
                profile.first_touch_referrer = normalized.get("first_touch_referrer")
                profile.landing_path = normalized.get("landing_path")

            if self._is_non_direct_source(normalized.get("first_touch_source")):
                profile.last_non_direct_source = normalized.get("first_touch_source")
                profile.last_non_direct_medium = normalized.get("first_touch_medium")
                profile.last_non_direct_campaign = normalized.get("first_touch_campaign")

            if not profile.first_touch_referrer and normalized.get("first_touch_referrer"):
                profile.first_touch_referrer = normalized.get("first_touch_referrer")
            if not profile.landing_path and normalized.get("landing_path"):
                profile.landing_path = normalized.get("landing_path")

        if not profile.acquisition_source or profile.acquisition_source == "unknown":
            profile.acquisition_source = self._resolve_acquisition_source(profile)

        self.db.add(profile)
        self.db.flush()
        return profile

    def mark_first_activated(self, *, user_id: int, occurred_at: datetime | None = None) -> UserGrowthProfile:
        profile = self._get_or_create_profile(user_id)
        if profile.first_activated_at is None:
            profile.first_activated_at = occurred_at or datetime.now(timezone.utc)
            self.db.add(profile)
            self.db.flush()
        return profile

    def mark_first_paid(self, *, user_id: int, occurred_at: datetime | None = None) -> UserGrowthProfile:
        profile = self._get_or_create_profile(user_id)
        if profile.first_paid_at is None:
            profile.first_paid_at = occurred_at or datetime.now(timezone.utc)
            self.db.add(profile)
            self.db.flush()
        return profile

    def record_event(
        self,
        *,
        user_id: int,
        event_name: str,
        public_model_code: str | None = None,
        route_group: str | None = None,
        provider_code: str | None = None,
        amount: Decimal | str | None = None,
        cost_amount: Decimal | str | None = None,
        power_amount: Decimal | str | None = None,
        currency: str | None = None,
        source_snapshot: dict[str, Any] | None = None,
        context_payload: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> BusinessEvent:
        profile = self._get_profile(user_id)
        event = BusinessEvent(
            user_id=user_id,
            event_name=event_name,
            public_model_code=public_model_code,
            route_group=route_group,
            provider_code=provider_code,
            amount=self._decimal_or_none(amount),
            cost_amount=self._decimal_or_none(cost_amount),
            power_amount=self._decimal_or_none(power_amount),
            currency=(currency or "").strip() or None,
            source_snapshot=source_snapshot or self._build_source_snapshot(profile),
            context_payload=context_payload or {},
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.flush()
        return event

    def serialize_growth_context(self, *, user_id: int) -> dict[str, Any]:
        profile = self._get_profile(user_id)
        if profile is None:
            return {
                "first_touch_source": None,
                "first_touch_medium": None,
                "first_touch_campaign": None,
                "first_touch_referrer": None,
                "landing_path": None,
                "last_non_direct_source": None,
                "last_non_direct_medium": None,
                "last_non_direct_campaign": None,
                "acquisition_source": "unknown",
                "customer_motion": "self_serve",
                "customer_segment": None,
                "first_activated_at": None,
                "first_paid_at": None,
            }
        return {
            "first_touch_source": profile.first_touch_source,
            "first_touch_medium": profile.first_touch_medium,
            "first_touch_campaign": profile.first_touch_campaign,
            "first_touch_referrer": profile.first_touch_referrer,
            "landing_path": profile.landing_path,
            "last_non_direct_source": profile.last_non_direct_source,
            "last_non_direct_medium": profile.last_non_direct_medium,
            "last_non_direct_campaign": profile.last_non_direct_campaign,
            "acquisition_source": profile.acquisition_source,
            "customer_motion": profile.customer_motion,
            "customer_segment": profile.customer_segment,
            "first_activated_at": profile.first_activated_at.isoformat() if profile.first_activated_at else None,
            "first_paid_at": profile.first_paid_at.isoformat() if profile.first_paid_at else None,
        }

    def _get_profile(self, user_id: int) -> UserGrowthProfile | None:
        return (
            self.db.query(UserGrowthProfile)
            .filter(UserGrowthProfile.user_id == user_id)
            .first()
        )

    def _get_or_create_profile(self, user_id: int) -> UserGrowthProfile:
        profile = self._get_profile(user_id)
        if profile is not None:
            return profile
        profile = UserGrowthProfile(user_id=user_id)
        self.db.add(profile)
        self.db.flush()
        return profile

    def _build_source_snapshot(self, profile: UserGrowthProfile | None) -> dict[str, Any]:
        if profile is None:
            return {}
        return {
            "first_touch_source": profile.first_touch_source,
            "first_touch_medium": profile.first_touch_medium,
            "first_touch_campaign": profile.first_touch_campaign,
            "first_touch_referrer": profile.first_touch_referrer,
            "landing_path": profile.landing_path,
            "last_non_direct_source": profile.last_non_direct_source,
            "last_non_direct_medium": profile.last_non_direct_medium,
            "last_non_direct_campaign": profile.last_non_direct_campaign,
            "acquisition_source": profile.acquisition_source,
            "customer_motion": profile.customer_motion,
            "customer_segment": profile.customer_segment,
        }

    def _resolve_acquisition_source(self, profile: UserGrowthProfile) -> str:
        if self._is_non_direct_source(profile.last_non_direct_source):
            return profile.last_non_direct_source or "unknown"
        if profile.first_touch_source:
            return profile.first_touch_source
        return "unknown"

    def _normalize_growth_context(self, growth_context: dict[str, Any] | None) -> dict[str, str]:
        payload = growth_context or {}
        normalized = {
            "first_touch_source": self._normalize_string(payload.get("first_touch_source"), limit=128),
            "first_touch_medium": self._normalize_string(payload.get("first_touch_medium"), limit=128),
            "first_touch_campaign": self._normalize_string(payload.get("first_touch_campaign"), limit=255),
            "first_touch_referrer": self._normalize_string(payload.get("first_touch_referrer"), limit=1024),
            "landing_path": self._normalize_string(payload.get("landing_path"), limit=1024),
        }
        return {key: value for key, value in normalized.items() if value}

    def _has_any_source(self, payload: dict[str, str]) -> bool:
        return any(payload.get(field) for field in ("first_touch_source", "first_touch_medium", "first_touch_campaign", "first_touch_referrer", "landing_path"))

    def _is_non_direct_source(self, value: str | None) -> bool:
        normalized = (value or "").strip().lower()
        return bool(normalized) and normalized not in _DIRECT_LIKE_VALUES

    def _normalize_string(self, value: Any, *, limit: int) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized[:limit]

    def _decimal_or_none(self, value: Decimal | str | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
