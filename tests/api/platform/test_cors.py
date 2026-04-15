from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


def test_cors_preflight_allows_configured_origin(monkeypatch):
    monkeypatch.setattr(settings, "cors_allowed_origins", "https://caller.example.com")
    app = create_app()
    client = TestClient(app)

    response = client.options(
        "/healthz",
        headers={
            "Origin": "https://caller.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://caller.example.com"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
