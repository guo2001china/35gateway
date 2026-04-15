from app.domains.platform.services.provider_options import ProviderOptionsService


def test_chain_mode_provider_options_follow_attempt_order() -> None:
    service = ProviderOptionsService(db=object())

    ordered = service.normalize_provider_options(
        [
            {"provider_code": "openai_official", "attempt_no": 2, "rank": 1},
            {"provider_code": "yunwu_openai", "attempt_no": 1, "rank": 2},
        ],
    )

    assert [item["provider_code"] for item in ordered] == ["yunwu_openai", "openai_official"]


def test_default_mode_provider_options_follow_attempt_order() -> None:
    service = ProviderOptionsService(db=object())

    ordered = service.normalize_provider_options(
        [
            {"provider_code": "openai_official", "attempt_no": 2, "rank": 1},
            {"provider_code": "yunwu_openai", "attempt_no": 1, "rank": 2},
        ],
    )

    assert [item["provider_code"] for item in ordered] == ["yunwu_openai", "openai_official"]
