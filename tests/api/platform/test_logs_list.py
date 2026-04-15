from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_access
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.user_console import UserConsoleService


def test_list_logs_route_forwards_pagination_and_filters(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=9, auth_mode="api_key")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    def fake_list_logs_paginated(
        self: UserConsoleService,
        *,
        user_id: int,
        page: int = 1,
        size: int = 20,
        status: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
    ) -> tuple[int, list[dict[str, object]]]:
        del self
        captured.update(
            {
                "user_id": user_id,
                "page": page,
                "size": size,
                "status": status,
                "model": model,
                "request_id": request_id,
            }
        )
        return (
            1,
            [
                {
                    "request_id": "req_test",
                    "created_at": "2026-03-23T00:00:00+00:00",
                    "model": "gpt-oss-120b",
                    "status": "succeeded",
                    "power_amount": "0.000000",
                    "duration_ms": 1234,
                }
            ],
        )

    monkeypatch.setattr(UserConsoleService, "list_logs_paginated", fake_list_logs_paginated)

    with TestClient(app) as client:
        response = client.get(
            "/v1/logs?page=3&size=15&status=succeeded&model=gpt-oss&request_id=req_",
            headers={"Authorization": "Bearer test-key"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page"] == 3
    assert response.json()["size"] == 15
    assert response.json()["items"][0]["request_id"] == "req_test"
    assert captured == {
        "user_id": 9,
        "page": 3,
        "size": 15,
        "status": "succeeded",
        "model": "gpt-oss",
        "request_id": "req_",
    }
