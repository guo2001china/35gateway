from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_session
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.redemption_codes import RedemptionCodeService


def test_redeem_redemption_code_route_succeeds(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_session] = lambda: UserAccessContext(user_id=31, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_redeem(self: RedemptionCodeService, *, user_id: int, code: str):
        del self
        assert user_id == 31
        assert code == "ABCD1234"
        return (
            SimpleNamespace(power_amount=Decimal("321.000000")),
            SimpleNamespace(recharge_order_no="rch_redeem_001"),
            SimpleNamespace(balance=Decimal("1321.000000")),
        )

    monkeypatch.setattr(RedemptionCodeService, "redeem", fake_redeem)

    with TestClient(app) as client:
        response = client.post(
            "/v1/redemption-codes/redeem",
            headers={"Authorization": "Bearer sess_api35_test"},
            json={"code": "ABCD1234"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "recharge_order_no": "rch_redeem_001",
        "balance_added": "321.000000",
        "balance": "1321.000000",
    }


def test_redeem_redemption_code_route_rejects_reused_code(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_session] = lambda: UserAccessContext(user_id=31, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_redeem(self: RedemptionCodeService, *, user_id: int, code: str):
        del self, user_id, code
        raise HTTPException(status_code=409, detail="redemption_code_already_used")

    monkeypatch.setattr(RedemptionCodeService, "redeem", fake_redeem)

    with TestClient(app) as client:
        response = client.post(
            "/v1/redemption-codes/redeem",
            headers={"Authorization": "Bearer sess_api35_test"},
            json={"code": "USED1234"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "redemption_code_already_used"


def test_redeem_redemption_code_route_rejects_invalid_code(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_session] = lambda: UserAccessContext(user_id=31, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    def fake_redeem(self: RedemptionCodeService, *, user_id: int, code: str):
        del self, user_id, code
        raise HTTPException(status_code=404, detail="redemption_code_not_found")

    monkeypatch.setattr(RedemptionCodeService, "redeem", fake_redeem)

    with TestClient(app) as client:
        response = client.post(
            "/v1/redemption-codes/redeem",
            headers={"Authorization": "Bearer sess_api35_test"},
            json={"code": "MISSING1234"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "redemption_code_not_found"
