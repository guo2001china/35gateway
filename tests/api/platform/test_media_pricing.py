from __future__ import annotations

from decimal import Decimal

from app.core.pricing.common import usd_to_cny
from app.core.pricing.quote import quote_request


def _quote(
    *,
    provider_code: str,
    route_group: str,
    execution_model_code: str,
    pricing_strategy: str,
    public_model_code: str,
    payload: dict[str, object],
) -> tuple[Decimal, str, dict[str, object]]:
    return quote_request(
        provider_code=provider_code,
        route_group=route_group,
        execution_model_code=execution_model_code,
        pricing_strategy=pricing_strategy,
        public_model_code=public_model_code,
        payload=payload,
    )


def test_quote_request_applies_margin_to_nano_banana() -> None:
    amount, currency, snapshot = _quote(
        provider_code="google_official",
        route_group="banana",
        execution_model_code="gemini-2.5-flash-image",
        pricing_strategy="image_banana_fixed",
        public_model_code="nano-banana",
        payload={"prompt": "draw a red apple"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert Decimal(snapshot["margin_amount"]) > Decimal("0")


def test_quote_request_applies_conservative_ksyun_cost_to_nano_banana() -> None:
    amount, currency, snapshot = _quote(
        provider_code="ksyun_openai",
        route_group="banana",
        execution_model_code="mgg-5-global",
        pricing_strategy="image_banana_fixed",
        public_model_code="nano-banana",
        payload={"prompt": "draw a red apple", "resolution": "1K"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == Decimal("0.45")
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_resolution_sensitive_ksyun_cost_to_nano_banana_2() -> None:
    amount, currency, snapshot = _quote(
        provider_code="ksyun_openai",
        route_group="banana",
        execution_model_code="mgg-9-global",
        pricing_strategy="image_banana_fixed_resolution",
        public_model_code="nano-banana-2",
        payload={"prompt": "draw a red apple", "resolution": "4K"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == Decimal("1.30")
    assert snapshot["request_factors"]["resolution"] == "4K"


def test_quote_request_applies_resolution_sensitive_ksyun_cost_to_nano_banana_pro() -> None:
    amount, currency, snapshot = _quote(
        provider_code="ksyun_openai",
        route_group="banana",
        execution_model_code="mgg-6-global",
        pricing_strategy="image_banana_fixed_resolution",
        public_model_code="nano-banana-pro",
        payload={"prompt": "draw a red apple", "resolution": "4K"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == Decimal("1.90")
    assert snapshot["request_factors"]["resolution"] == "4K"


def test_quote_request_resolves_ksyun_text_alias_to_gpt_54_pricing() -> None:
    amount, currency, snapshot = _quote(
        provider_code="ksyun_openai",
        route_group="openai",
        execution_model_code="mog-3-global",
        pricing_strategy="text_tokens",
        public_model_code="gpt-5.4",
        payload={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 64,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_margin_to_minimax_m27_text() -> None:
    amount, currency, snapshot = _quote(
        provider_code="minimax_official",
        route_group="openai",
        execution_model_code="MiniMax-M2.7",
        pricing_strategy="text_tokens",
        public_model_code="MiniMax-M2.7",
        payload={
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 32,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_margin_to_minimax_turbo_tts() -> None:
    amount, currency, snapshot = _quote(
        provider_code="minimax_official",
        route_group="minimax_t2a_async",
        execution_model_code="speech-2.8-turbo",
        pricing_strategy="audio_minimax_t2a",
        public_model_code="speech-2.8-turbo",
        payload={
            "model": "speech-2.8-turbo",
            "text": "hello world",
            "voice_setting": {"voice_id": "English_expressive_narrator"},
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_margin_to_seedream() -> None:
    amount, currency, snapshot = _quote(
        provider_code="volcengine_seedream",
        route_group="seedream",
        execution_model_code="doubao-seedream-5-0-lite-260128",
        pricing_strategy="image_seedream",
        public_model_code="doubao-seedream-5.0-lite",
        payload={"prompt": "minimal poster"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_margin_to_seedream_45() -> None:
    amount, currency, snapshot = _quote(
        provider_code="volcengine_seedream",
        route_group="seedream",
        execution_model_code="doubao-seedream-4-5-251128",
        pricing_strategy="image_seedream",
        public_model_code="doubao-seedream-4.5",
        payload={"prompt": "premium poster", "size": "4096x2304"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["size"] == "4096x2304"


def test_quote_request_applies_margin_to_veo() -> None:
    amount, currency, snapshot = _quote(
        provider_code="google_veo3",
        route_group="veo31",
        execution_model_code="veo-3.1-fast-generate-preview",
        pricing_strategy="video_veo",
        public_model_code="veo-3.1-fast",
        payload={"prompt": "clean commercial shot", "seconds": 4, "resolution": "720p", "generate_audio": True},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_fal_seedance_fast_costs() -> None:
    amount, currency, snapshot = _quote(
        provider_code="fal_seedance20",
        route_group="seedance",
        execution_model_code="seedance-2.0-fast",
        pricing_strategy="video_seedance",
        public_model_code="seedance-2.0-fast",
        payload={"prompt": "clean commercial shot", "seconds": 4, "resolution": "720p", "generate_audio": True},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == usd_to_cny("0.2419") * Decimal("4")
    assert snapshot["request_factors"]["input_mode"] == "text"
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_fal_veo3_costs() -> None:
    amount, currency, snapshot = _quote(
        provider_code="fal_veo3",
        route_group="veo3",
        execution_model_code="veo-3-fast",
        pricing_strategy="video_veo",
        public_model_code="veo-3-fast",
        payload={"prompt": "clean commercial shot", "seconds": 4, "resolution": "1080p", "generate_audio": False},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["cost_amount"]) == usd_to_cny("0.25") * Decimal("4")
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")


def test_quote_request_applies_margin_to_minimax_video() -> None:
    amount, currency, snapshot = _quote(
        provider_code="minimax_official",
        route_group="minimax_video",
        execution_model_code="MiniMax-Hailuo-02",
        pricing_strategy="video_minimax",
        public_model_code="minimax-hailuo-02",
        payload={
            "prompt": "clean product shot",
            "input_reference": "https://example.com/frame.png",
            "resolution": "512P",
            "seconds": 6,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["input_mode"] == "image"


def test_quote_request_applies_margin_to_wan_video() -> None:
    amount, currency, snapshot = _quote(
        provider_code="wan_official",
        route_group="wan_video",
        execution_model_code="wan2.6",
        pricing_strategy="video_wan",
        public_model_code="wan2.6",
        payload={
            "prompt": "clean product shot",
            "reference_urls": ["https://example.com/ref-a.png"],
            "resolution": "1080P",
            "seconds": 5,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["input_mode"] == "reference"
    assert snapshot["request_factors"]["resolved_model"] == "wan2.6-r2v"


def test_quote_request_applies_margin_to_wan_flash_silent_video() -> None:
    amount, currency, snapshot = _quote(
        provider_code="wan_official",
        route_group="wan_video",
        execution_model_code="wan2.6-flash",
        pricing_strategy="video_wan",
        public_model_code="wan2.6-flash",
        payload={
            "input_reference": "https://example.com/frame.png",
            "generate_audio": False,
            "resolution": "720P",
            "seconds": 5,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["resolved_model"] == "wan2.6-i2v-flash"
    assert snapshot["request_factors"]["generate_audio"] is False


def test_quote_request_applies_margin_to_kling_video() -> None:
    amount, currency, snapshot = _quote(
        provider_code="kling_official",
        route_group="kling_video",
        execution_model_code="kling-video-o1",
        pricing_strategy="video_kling",
        public_model_code="kling-o1",
        payload={
            "prompt": "Create a sequel shot using this reference clip.",
            "video_url": "https://example.com/reference.mp4",
            "mode": "std",
            "seconds": 5,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["input_mode"] == "video_reference"
    assert snapshot["request_factors"]["mode"] == "std"
    assert snapshot["request_factors"]["has_video_input"] is True
    assert snapshot["request_factors"]["resolved_model"] == "kling-video-o1"


def test_quote_request_applies_margin_to_vidu_q3() -> None:
    amount, currency, snapshot = _quote(
        provider_code="vidu_official",
        route_group="vidu",
        execution_model_code="viduq3-pro",
        pricing_strategy="video_vidu",
        public_model_code="viduq3-pro",
        payload={
            "mode": "image",
            "images": ["https://example.com/frame.png"],
            "duration": 5,
            "resolution": "720p",
            "audio": True,
            "off_peak": True,
            "is_rec": True,
        },
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
    assert snapshot["request_factors"]["mode"] == "image"
    assert snapshot["request_factors"]["credits"] == "75"


def test_quote_request_applies_margin_to_qwen_tts() -> None:
    amount, currency, snapshot = _quote(
        provider_code="qwen_official",
        route_group="qwen_tts",
        execution_model_code="qwen3-tts-vc-2026-01-22",
        pricing_strategy="audio_qwen_tts",
        public_model_code="qwen3-tts-vc-2026-01-22",
        payload={"text": "你好，欢迎使用 API35。"},
    )

    assert currency == "CNY"
    assert amount == Decimal(snapshot["sale_amount"])
    assert Decimal(snapshot["sale_amount"]) > Decimal(snapshot["cost_amount"]) > Decimal("0")
