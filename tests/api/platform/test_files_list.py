from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_access
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.files import FileService


def test_list_files_route_forwards_pagination_and_kind(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=9, auth_mode="session")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    def fake_list_files(
        self: FileService,
        *,
        user_id: int,
        page: int = 1,
        size: int = 20,
        kind: str | None = None,
    ) -> tuple[int, list[dict[str, object]]]:
        del self
        captured.update(
            {
                "user_id": user_id,
                "page": page,
                "size": size,
                "kind": kind,
            }
        )
        return (
            1,
            [
                {
                    "file_id": "file_uploaded",
                    "filename": "poster.png",
                    "content_type": "image/png",
                    "size": 4,
                    "kind": "image",
                    "status": "uploaded",
                    "bucket": "bucket-a",
                    "object_key": "uploads/9/poster.png",
                    "url": "https://signed.example.com/poster.png",
                    "etag": None,
                    "created_at": "2026-03-23T00:00:00+00:00",
                    "completed_at": "2026-03-23T00:00:00+00:00",
                }
            ],
        )

    monkeypatch.setattr(FileService, "list_files", fake_list_files)

    with TestClient(app) as client:
        response = client.get(
            "/v1/files?page=2&size=10&kind=image",
            headers={"Authorization": "Bearer test-key"},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page"] == 2
    assert response.json()["size"] == 10
    assert response.json()["items"][0]["file_id"] == "file_uploaded"
    assert captured == {
        "user_id": 9,
        "page": 2,
        "size": 10,
        "kind": "image",
    }
