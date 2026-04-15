from __future__ import annotations

import socket

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_access
from app.api.deps import get_db
from app.main import create_app
from app.domains.platform.services.files import FileService


class _FakeStreamContext:
    def __init__(self, response: httpx.Response):
        self._response = response

    def __enter__(self) -> httpx.Response:
        return self._response

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._response.close()
        return False


class _FakeHttpxClient:
    def __init__(self, responses: list[httpx.Response], **_: object):
        self._responses = iter(responses)

    def __enter__(self) -> _FakeHttpxClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def stream(self, method: str, url: str, headers: dict[str, str] | None = None) -> _FakeStreamContext:
        del method, url, headers
        return _FakeStreamContext(next(self._responses))


def test_import_url_route_forwards_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=9, auth_mode="api_key")
    app.dependency_overrides[get_db] = lambda: iter([object()])

    captured: dict[str, object] = {}

    def fake_import(
        self: FileService,
        *,
        user_id: int,
        url: str,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, object]:
        del self
        captured.update(
            {
                "user_id": user_id,
                "url": url,
                "filename": filename,
                "content_type": content_type,
            }
        )
        return {
            "file_id": "file_imported",
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

    monkeypatch.setattr(FileService, "import_file_from_url", fake_import)

    with TestClient(app) as client:
        response = client.post(
            "/v1/files/import-url",
            headers={"Authorization": "Bearer test-key"},
            json={
                "url": "https://example.com/assets/poster.png",
                "filename": "poster.png",
                "content_type": "image/png",
            },
        )

    assert response.status_code == 201
    assert response.json()["file_id"] == "file_imported"
    assert captured == {
        "user_id": 9,
        "url": "https://example.com/assets/poster.png",
        "filename": "poster.png",
        "content_type": "image/png",
    }


def test_import_file_from_url_downloads_and_reuses_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FileService(db=object())
    monkeypatch.setattr(FileService, "_require_user", lambda self, user_id: object())
    monkeypatch.setattr(FileService, "_require_oss_ready", lambda self: None)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, type=0: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))],
    )

    response = httpx.Response(
        200,
        headers={"content-type": "image/png", "content-length": "4"},
        content=b"data",
        request=httpx.Request("GET", "https://files.example.com/assets/poster.png"),
    )
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeHttpxClient([response], **kwargs))

    captured: dict[str, object] = {}

    def fake_upload(
        self: FileService,
        *,
        user_id: int,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, object]:
        del self
        captured.update(
            {
                "user_id": user_id,
                "filename": filename,
                "content_type": content_type,
                "content": content,
            }
        )
        return {"file_id": "file_ok"}

    monkeypatch.setattr(FileService, "upload_file", fake_upload)

    result = service.import_file_from_url(user_id=7, url="https://files.example.com/assets/poster.png")

    assert result == {"file_id": "file_ok"}
    assert captured == {
        "user_id": 7,
        "filename": "poster.png",
        "content_type": "image/png",
        "content": b"data",
    }


def test_import_file_from_url_rejects_private_host(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FileService(db=object())
    monkeypatch.setattr(FileService, "_require_user", lambda self, user_id: object())
    monkeypatch.setattr(FileService, "_require_oss_ready", lambda self: None)

    with pytest.raises(HTTPException) as exc_info:
        service.import_file_from_url(user_id=1, url="http://127.0.0.1/internal.png")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "remote_host_not_public"
