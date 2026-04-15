from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_model_catalog_routes_return_snapshot_backed_payloads() -> None:
    app = create_app()

    with TestClient(app) as client:
        listed = client.get("/v1/models")
        detail = client.get("/v1/models/DeepSeek-V3.2")
        providers = client.get("/v1/models/DeepSeek-V3.2/providers")

    assert listed.status_code == 200
    listed_payload = listed.json()
    assert listed_payload
    deepseek_row = next(item for item in listed_payload if item["model_code"] == "DeepSeek-V3.2")
    assert deepseek_row["category"] == "text"
    assert deepseek_row["create_endpoint"] == "POST /v1/chat/completions"
    assert deepseek_row["provider_count"] >= 1

    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["model_code"] == "DeepSeek-V3.2"
    assert detail_payload["route_group"] == "openai"
    assert detail_payload["endpoints"].get("create") == "POST /v1/chat/completions"
    assert detail_payload["providers"]

    assert providers.status_code == 200
    provider_payload = providers.json()
    assert provider_payload
    first_provider = provider_payload[0]
    assert first_provider["route_group"] == "openai"
    assert first_provider["execution_model_code"]
