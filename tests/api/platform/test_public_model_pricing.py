from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.auth import UserAccessContext, require_user_access
from app.db.session import SessionLocal
from app.domains.platform.entities.entities import ApiKey, ModelMetricsHourly, User
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.platform.services.public_model_pricing import PublicModelPricingService
from app.main import create_app


def _find_item(items: list[dict[str, object]], model_code: str) -> dict[str, object]:
    for item in items:
        if item["model_code"] == model_code:
            return item
    raise AssertionError(f"model_not_found:{model_code}")


def _assert_relative_order(items: list[str], *model_codes: str) -> None:
    missing = [model_code for model_code in model_codes if model_code not in items]
    assert not missing, f"missing expected model codes: {missing}"
    positions = [items.index(model_code) for model_code in model_codes]
    assert positions == sorted(positions), f"unexpected order: items={items}, expected={model_codes}"


def _create_user_and_api_key():
    with SessionLocal() as db:
        user = User(
            user_no=f"u_pricing_{uuid4().hex[:12]}",
            name=f"Pricing User {uuid4().hex[:8]}",
            balance=Decimal("1000.000000"),
            status="active",
        )
        db.add(user)
        db.flush()
        api_key = ApiKey(
            user_id=user.id,
            key_name="Pricing Key",
            key_kind="user_created",
            key_plaintext=f"ak_api35_pricing_{uuid4().hex[:12]}",
            key_hash=f"hash_{uuid4().hex}",
            status="active",
        )
        db.add(api_key)
        db.commit()
        db.refresh(user)
        db.refresh(api_key)
        return user.id, api_key.id


def _primary_route_group(model_code: str) -> str:
    route = get_platform_config_snapshot().get_primary_route(model_code, public_only=True)
    if route is None:
        raise AssertionError(f"missing_primary_route:{model_code}")
    return route.route_group


def test_model_pricing_service_returns_public_models() -> None:
    with SessionLocal() as db:
        items = PublicModelPricingService(db).list_models()

    qwen_tts = _find_item(items, "qwen3-tts-flash")
    minimax_tts = _find_item(items, "speech-2.8-hd")
    minimax_turbo = _find_item(items, "speech-2.8-turbo")
    minimax_text = _find_item(items, "MiniMax-M2.7")
    gpt = _find_item(items, "gpt-5.4")
    seedance_standard = _find_item(items, "seedance-2.0")
    seedance_fast = _find_item(items, "seedance-2.0-fast")
    seedream_45 = _find_item(items, "doubao-seedream-4.5")

    assert qwen_tts["category"] == "audio"
    assert qwen_tts["supported_input_modes"] == ["text_to_speech"]
    assert qwen_tts["pricing"]["price_lines"][0]["label"] == "参考价"
    assert minimax_tts["pricing"]["price_lines"][0]["label"] == "参考价"
    assert minimax_turbo["pricing"]["price_lines"][0]["label"] == "参考价"
    assert minimax_text["pricing"]["price_lines"][0]["label"] == "输入"
    assert gpt["pricing"]["price_lines"][0]["label"] == "输入"
    assert all(line["label"] != "百字预计" for line in gpt["pricing"]["price_lines"])
    assert seedance_fast["pricing"]["price_lines"] == [{"label": "参考价", "value": "¥1.8815 / 秒"}]
    assert seedance_standard["pricing"]["price_lines"] == [
        {"label": "文生", "value": "¥2.3598 / 秒"},
        {"label": "图生", "value": "¥2.352 / 秒"},
    ]
    assert seedream_45["pricing"]["price_lines"][0]["label"] == "参考价"


def test_model_pricing_service_sorts_by_release_recency_within_category() -> None:
    with SessionLocal() as db:
        items = PublicModelPricingService(db).list_models()

    categories = [str(item["category"]) for item in items]
    first_image = categories.index("image")
    first_video = categories.index("video")
    first_audio = categories.index("audio")
    last_text = len(categories) - 1 - categories[::-1].index("text")
    last_image = len(categories) - 1 - categories[::-1].index("image")
    last_video = len(categories) - 1 - categories[::-1].index("video")

    assert last_text < first_image < first_video < first_audio
    assert last_image < first_video
    assert last_video < first_audio

    text_items = [str(item["model_code"]) for item in items if item["category"] == "text"]
    image_items = [str(item["model_code"]) for item in items if item["category"] == "image"]
    video_items = [str(item["model_code"]) for item in items if item["category"] == "video"]
    audio_items = [str(item["model_code"]) for item in items if item["category"] == "audio"]

    assert text_items[0] == "gpt-5.4"
    assert image_items[0] == "doubao-seedream-5.0-lite"
    assert video_items[0] == "seedance-2.0-fast"
    assert audio_items[0] == "speech-2.8-hd"

    _assert_relative_order(
        text_items,
        "gpt-5.4",
        "gpt-5.4-pro",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gemini-3.1-pro-preview",
    )
    _assert_relative_order(
        image_items,
        "doubao-seedream-5.0-lite",
        "nano-banana-2",
        "nano-banana-pro",
        "doubao-seedream-4.5",
        "nano-banana",
    )
    _assert_relative_order(video_items, "seedance-2.0-fast", "seedance-2.0", "veo-3.1-fast", "veo-3.1", "veo-3-fast", "veo-3")
    _assert_relative_order(audio_items, "speech-2.8-hd", "speech-2.8-turbo", "qwen3-tts-instruct-flash")


def test_model_pricing_route_returns_sanitized_public_list() -> None:
    app = create_app()
    app.dependency_overrides[require_user_access] = lambda: UserAccessContext(user_id=21, auth_mode="session")

    with TestClient(app) as client:
        response = client.get("/v1/model-pricing", headers={"Authorization": "Bearer test-key"})

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["model_code"] == "qwen3-tts-flash" for item in payload)
    assert any(item["model_code"] == "seedance-2.0-fast" for item in payload)
    assert any(item["model_code"] == "veo-3.1-fast" for item in payload)
    assert all("providers" not in item for item in payload)
    assert all("status" not in item["pricing"] for item in payload)
    assert all("last_verified_at" not in item["pricing"] for item in payload)
    assert all("availability" in item for item in payload)


def test_model_pricing_service_includes_sync_model_availability_when_sample_ready() -> None:
    route_group = _primary_route_group("gpt-5.4")
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.add(
            ModelMetricsHourly(
                bucket_start=now.replace(minute=0, second=0, microsecond=0),
                public_model_code="gpt-5.4",
                route_group=route_group,
                sample_count=20,
                success_count=18,
                request_sample_count=20,
                request_success_count=18,
                task_sample_count=0,
                task_success_count=0,
            )
        )
        db.commit()

        items = PublicModelPricingService(db).list_models()

    gpt = _find_item(items, "gpt-5.4")
    assert gpt["availability"] == {"window": "24h", "sample_count": 20, "success_rate": 90.0}


def test_model_pricing_service_includes_async_model_availability_when_sample_ready() -> None:
    route_group = _primary_route_group("veo-3.1")
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.add(
            ModelMetricsHourly(
                bucket_start=now.replace(minute=0, second=0, microsecond=0),
                public_model_code="veo-3.1",
                route_group=route_group,
                sample_count=20,
                success_count=17,
                request_sample_count=0,
                request_success_count=0,
                task_sample_count=20,
                task_success_count=17,
            )
        )
        db.commit()

        items = PublicModelPricingService(db).list_models()

    veo = _find_item(items, "veo-3.1")
    assert veo["availability"] == {"window": "24h", "sample_count": 20, "success_rate": 85.0}


def test_model_pricing_service_hides_availability_below_sample_threshold() -> None:
    route_group = _primary_route_group("MiniMax-M2.7")
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        db.add(
            ModelMetricsHourly(
                bucket_start=now.replace(minute=0, second=0, microsecond=0),
                public_model_code="MiniMax-M2.7",
                route_group=route_group,
                sample_count=19,
                success_count=19,
                request_sample_count=19,
                request_success_count=19,
                task_sample_count=0,
                task_success_count=0,
            )
        )
        db.commit()

        items = PublicModelPricingService(db).list_models()

    minimax = _find_item(items, "MiniMax-M2.7")
    assert minimax["availability"] is None
