from __future__ import annotations

from .common import provider_env
from .types import ProviderConfig


def build_fal_providers() -> dict[str, ProviderConfig]:
    providers: dict[str, ProviderConfig] = {}

    seedance20_api_key = (
        provider_env("API35_FAL_SEEDANCE20_API_KEY", "").strip()
        or provider_env("API35_FAL_VEO31_API_KEY", "").strip()
        or provider_env("API35_FAL_VEO3_API_KEY", "").strip()
    )
    veo31_api_key = provider_env("API35_FAL_VEO31_API_KEY", "").strip()
    veo3_api_key = provider_env("API35_FAL_VEO3_API_KEY", "").strip() or veo31_api_key
    providers["fal_veo3"] = ProviderConfig(
        provider_code="fal_veo3",
        provider_name="Fal Veo 3",
        adapter_key="fal",
        base_url=provider_env(
            "API35_FAL_VEO3_BASE_URL",
            provider_env("API35_FAL_VEO31_BASE_URL", "https://fal.run"),
        ),
        auth_type="key",
        auth_config={
            "api_key": veo3_api_key,
            "queue_base_url": provider_env("API35_FAL_QUEUE_BASE_URL", "https://queue.fal.run"),
            "veo3_create_path": provider_env(
                "API35_FAL_VEO3_CREATE_PATH",
                "/fal-ai/veo3",
            ),
            "veo3_image_create_path": provider_env(
                "API35_FAL_VEO3_IMAGE_CREATE_PATH",
                "/fal-ai/veo3/image-to-video",
            ),
            "veo3_fast_create_path": provider_env(
                "API35_FAL_VEO3_FAST_CREATE_PATH",
                "/fal-ai/veo3/fast",
            ),
            "veo3_fast_image_create_path": provider_env(
                "API35_FAL_VEO3_FAST_IMAGE_CREATE_PATH",
                "/fal-ai/veo3/fast/image-to-video",
            ),
        },
    )

    providers["fal_seedance20"] = ProviderConfig(
        provider_code="fal_seedance20",
        provider_name="Fal Seedance 2.0",
        adapter_key="fal",
        base_url=provider_env("API35_FAL_SEEDANCE20_BASE_URL", "https://fal.run"),
        auth_type="key",
        auth_config={
            "api_key": seedance20_api_key,
            "queue_base_url": provider_env("API35_FAL_QUEUE_BASE_URL", "https://queue.fal.run"),
            "seedance20_text_create_path": provider_env(
                "API35_FAL_SEEDANCE20_TEXT_CREATE_PATH",
                "/bytedance/seedance-2.0/text-to-video",
            ),
            "seedance20_image_create_path": provider_env(
                "API35_FAL_SEEDANCE20_IMAGE_CREATE_PATH",
                "/bytedance/seedance-2.0/image-to-video",
            ),
            "seedance20_fast_text_create_path": provider_env(
                "API35_FAL_SEEDANCE20_FAST_TEXT_CREATE_PATH",
                "/bytedance/seedance-2.0/fast/text-to-video",
            ),
            "seedance20_fast_image_create_path": provider_env(
                "API35_FAL_SEEDANCE20_FAST_IMAGE_CREATE_PATH",
                "/bytedance/seedance-2.0/fast/image-to-video",
            ),
        },
    )

    providers["fal_veo31"] = ProviderConfig(
        provider_code="fal_veo31",
        provider_name="Fal Veo 3.1",
        adapter_key="fal",
        base_url=provider_env("API35_FAL_VEO31_BASE_URL", "https://fal.run"),
        auth_type="key",
        auth_config={
            "api_key": veo31_api_key,
            "queue_base_url": provider_env("API35_FAL_QUEUE_BASE_URL", "https://queue.fal.run"),
            "veo31_create_path": provider_env(
                "API35_FAL_VEO31_CREATE_PATH",
                "/fal-ai/veo3.1",
            ),
            "veo31_image_create_path": provider_env(
                "API35_FAL_VEO31_IMAGE_CREATE_PATH",
                "/fal-ai/veo3.1/image-to-video",
            ),
            "veo31_first_last_create_path": provider_env(
                "API35_FAL_VEO31_FIRST_LAST_CREATE_PATH",
                "/fal-ai/veo3.1/first-last-frame-to-video",
            ),
            "veo31_reference_create_path": provider_env(
                "API35_FAL_VEO31_REFERENCE_CREATE_PATH",
                "/fal-ai/veo3.1/reference-to-video",
            ),
            "veo31_fast_create_path": provider_env(
                "API35_FAL_VEO31_FAST_CREATE_PATH",
                "/fal-ai/veo3.1/fast",
            ),
            "veo31_fast_image_create_path": provider_env(
                "API35_FAL_VEO31_FAST_IMAGE_CREATE_PATH",
                "/fal-ai/veo3.1/fast/image-to-video",
            ),
            "veo31_fast_first_last_create_path": provider_env(
                "API35_FAL_VEO31_FAST_FIRST_LAST_CREATE_PATH",
                "/fal-ai/veo3.1/fast/first-last-frame-to-video",
            ),
            "veo31_fast_extend_create_path": provider_env(
                "API35_FAL_VEO31_FAST_EXTEND_CREATE_PATH",
                "/fal-ai/veo3.1/fast/extend-video",
            ),
        },
    )

    nano_banana_api_key = provider_env("API35_FAL_NANO_BANANA_API_KEY", "").strip()
    providers["fal_nano_banana"] = ProviderConfig(
        provider_code="fal_nano_banana",
        provider_name="Fal Nano Banana",
        adapter_key="fal",
        base_url=provider_env("API35_FAL_NANO_BANANA_BASE_URL", "https://fal.run"),
        auth_type="key",
        auth_config={
            "api_key": nano_banana_api_key,
            "nano_banana_create_path": provider_env(
                "API35_FAL_NANO_BANANA_CREATE_PATH",
                "/fal-ai/nano-banana",
            ),
            "nano_banana_edit_path": provider_env(
                "API35_FAL_NANO_BANANA_EDIT_PATH",
                "/fal-ai/nano-banana/edit",
            ),
            "nano_banana_pro_create_path": provider_env(
                "API35_FAL_NANO_BANANA_PRO_CREATE_PATH",
                "/fal-ai/nano-banana-pro",
            ),
            "nano_banana_pro_edit_path": provider_env(
                "API35_FAL_NANO_BANANA_PRO_EDIT_PATH",
                "/fal-ai/nano-banana-pro/edit",
            ),
            "nano_banana_2_create_path": provider_env(
                "API35_FAL_NANO_BANANA_2_CREATE_PATH",
                "/fal-ai/nano-banana-2",
            ),
            "nano_banana_2_edit_path": provider_env(
                "API35_FAL_NANO_BANANA_2_EDIT_PATH",
                "/fal-ai/nano-banana-2/edit",
            ),
        },
    )

    return providers


FAL_PROVIDERS: dict[str, ProviderConfig] = build_fal_providers()
