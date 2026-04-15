from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.db.session import SessionLocal
from app.domains.platform.entities.entities import BusinessEvent, User
from app.domains.platform.services.business_tracking import BusinessTrackingService


def test_business_tracking_syncs_growth_profile_and_records_event() -> None:
    unique = uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        user = User(
            user_no=f"u_growth_{unique}",
            name=f"Growth User {unique}",
            balance=Decimal("0"),
            status="active",
            created_at=now,
        )
        db.add(user)
        db.flush()

        service = BusinessTrackingService(db)
        profile = service.sync_growth_context(
            user_id=user.id,
            growth_context={
                "first_touch_source": "seo_docs",
                "first_touch_medium": "organic",
                "first_touch_campaign": "gemini-pricing",
                "landing_path": "/models/gemini-2.5-pro",
            },
        )
        service.mark_first_activated(user_id=user.id, occurred_at=now)
        service.mark_first_paid(user_id=user.id, occurred_at=now)
        service.record_event(
            user_id=user.id,
            event_name="billing_succeeded",
            public_model_code="gemini-2.5-pro",
            route_group="openai",
            provider_code="openai_official",
            amount=Decimal("12.34"),
            cost_amount=Decimal("9.99"),
            power_amount=Decimal("12340"),
            currency="CNY",
        )
        db.commit()
        db.refresh(profile)

        assert profile.first_touch_source == "seo_docs"
        assert profile.last_non_direct_source == "seo_docs"
        assert profile.acquisition_source == "seo_docs"
        assert profile.first_activated_at is not None
        assert profile.first_paid_at is not None

        event = (
            db.query(BusinessEvent)
            .filter(BusinessEvent.user_id == user.id, BusinessEvent.event_name == "billing_succeeded")
            .order_by(BusinessEvent.id.desc())
            .first()
        )
        assert event is not None
        assert event.source_snapshot["acquisition_source"] == "seo_docs"
        assert event.public_model_code == "gemini-2.5-pro"
