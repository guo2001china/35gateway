from __future__ import annotations

from typing import Any


QWEN_TTS_SYSTEM_FLASH_MODEL = "qwen3-tts-flash"
QWEN_TTS_SYSTEM_INSTRUCT_FLASH_MODEL = "qwen3-tts-instruct-flash"
QWEN_TTS_CLONED_VOICE_MODEL = "qwen3-tts-vc-2026-01-22"
QWEN_SYSTEM_TTS_MODE_STANDARD = "standard"
QWEN_SYSTEM_TTS_MODE_INSTRUCT = "instruct"

QWEN_API35_SYSTEM_TTS_MODELS = (
    QWEN_TTS_SYSTEM_FLASH_MODEL,
    QWEN_TTS_SYSTEM_INSTRUCT_FLASH_MODEL,
)
QWEN_API35_TTS_MODELS = (
    *QWEN_API35_SYSTEM_TTS_MODELS,
    QWEN_TTS_CLONED_VOICE_MODEL,
)

QWEN_TTS_FULL_MODELS = [
    "qwen-tts-latest",
    "qwen-tts",
    "qwen-tts-flash-latest",
    "qwen-tts-flash",
    "qwen-tts-flash-instruct-latest",
    "qwen-tts-flash-instruct",
]

QWEN_TTS_STANDARD_MODELS = [
    "qwen-tts-latest",
    "qwen-tts",
    "qwen-tts-flash-latest",
    "qwen-tts-flash",
]

QWEN_TTS_FLASH_MODELS = [
    "qwen-tts-flash-instruct-latest",
    "qwen-tts-flash-instruct",
    "qwen-tts-flash-latest",
    "qwen-tts-flash",
]

QWEN_TTS_FLASH_ONLY_MODELS = [
    "qwen-tts-flash-latest",
    "qwen-tts-flash",
]

QWEN_API35_SYSTEM_TTS_STANDARD_MODEL_ALIASES = {
    "qwen-tts-flash-latest",
    "qwen-tts-flash",
}

QWEN_API35_SYSTEM_TTS_INSTRUCT_MODEL_ALIASES = {
    "qwen-tts-flash-instruct-latest",
    "qwen-tts-flash-instruct",
}

QWEN_API35_SYSTEM_TTS_SUPPORTED_MODEL_ALIASES = (
    QWEN_API35_SYSTEM_TTS_STANDARD_MODEL_ALIASES | QWEN_API35_SYSTEM_TTS_INSTRUCT_MODEL_ALIASES
)

QWEN_SYSTEM_TTS_MODES = (
    QWEN_SYSTEM_TTS_MODE_STANDARD,
    QWEN_SYSTEM_TTS_MODE_INSTRUCT,
)

QWEN_SYSTEM_TTS_MODE_TO_MODEL = {
    QWEN_SYSTEM_TTS_MODE_STANDARD: QWEN_TTS_SYSTEM_FLASH_MODEL,
    QWEN_SYSTEM_TTS_MODE_INSTRUCT: QWEN_TTS_SYSTEM_INSTRUCT_FLASH_MODEL,
}

QWEN_MULTILINGUAL_LANGUAGE_CODES = (
    "zh",
    "en",
    "fr",
    "de",
    "ru",
    "it",
    "es",
    "pt",
    "ja",
    "ko",
)


def _languages_for_locale(locale: str) -> list[str]:
    normalized_locale = locale.strip().lower()
    if normalized_locale == "multilingual":
        return list(QWEN_MULTILINGUAL_LANGUAGE_CODES)

    language = normalized_locale.split("-", 1)[0]
    return [language] if language else []


def _voice(
    voice: str,
    *,
    locale: str,
    description: str,
    supported_models: list[str],
    languages: list[str] | None = None,
    enabled_modes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "voice": voice,
        "locale": locale,
        "languages": list(languages or _languages_for_locale(locale)),
        "description": description,
        "supported_models": supported_models,
        "enabled_modes": list(enabled_modes) if enabled_modes is not None else None,
    }


QWEN_SYSTEM_VOICES: tuple[dict[str, Any], ...] = (
    _voice(
        "Cherry",
        locale="multilingual",
        description="温柔成熟女声，适合客服、有声内容和导航播报。",
        supported_models=QWEN_TTS_FULL_MODELS,
        enabled_modes=list(QWEN_SYSTEM_TTS_MODES),
    ),
    _voice(
        "Serena",
        locale="multilingual",
        description="沉稳温柔女声，适合客服、导航和有声读物。",
        supported_models=QWEN_TTS_FULL_MODELS,
        enabled_modes=list(QWEN_SYSTEM_TTS_MODES),
    ),
    _voice(
        "Ethan",
        locale="multilingual",
        description="沉稳温和男声，适合有声内容、客服和导航播报。",
        supported_models=QWEN_TTS_FULL_MODELS,
        enabled_modes=list(QWEN_SYSTEM_TTS_MODES),
    ),
    _voice("Chelsie", locale="multilingual", description="知性年轻女声，适合新闻播报和有声内容。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Callie", locale="multilingual", description="中英双语女声，适合客服和有声内容。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Merry", locale="multilingual", description="甜美女声，适合导航、助手和有声内容。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Kangkang", locale="multilingual", description="中年男声，适合综艺、助手和视频配音。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Junyang", locale="multilingual", description="浑厚老年男声，适合有声内容和视频配音。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Enya", locale="multilingual", description="温柔成熟知性女声，适合有声内容和视频配音。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Canna", locale="multilingual", description="甜美卡通女孩音色，适合助手、导航和视频配音。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Bunny", locale="multilingual", description="稚嫩儿童男声音色，适合助手和有声内容。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Anna", locale="multilingual", description="活力女主播音色，适合新闻和视频配音。", supported_models=QWEN_TTS_FULL_MODELS),
    _voice("Ember", locale="en-US", description="平静的年轻女声，适合客服、有声内容和导航播报。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Diana", locale="zh-CN", description="标准普通话女青年音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Mike", locale="zh-CN", description="标准普通话男青年音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Chloe", locale="zh-CN", description="知性普通话女青年音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Dylan", locale="zh-CN", description="标准普通话男青年音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Momo", locale="zh-CN-yue", description="广东话女声音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Vivian", locale="zh-CN-yue", description="广东话女声音色。", supported_models=QWEN_TTS_FLASH_MODELS),
    _voice("Sofia", locale="zh-CN-sichuan", description="四川话女声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Jada", locale="zh-CN-sichuan", description="四川话男声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Sunny", locale="zh-CN-sichuan", description="四川话男声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Mandy", locale="zh-CN-shanghai", description="上海话女声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Apple", locale="zh-CN-shanghai", description="上海话女声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Matthew", locale="zh-CN-beijing", description="北京话男声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("William", locale="zh-CN-beijing", description="北京话男声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Lily", locale="zh-CN-henan", description="河南话女声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Liam", locale="zh-CN-hubei", description="湖北话男声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Ava", locale="zh-CN-shaanxi", description="陕西话女声音色。", supported_models=QWEN_TTS_STANDARD_MODELS),
    _voice("Bella", locale="zh-CN-tianjin", description="天津话女声音色。", supported_models=QWEN_TTS_FLASH_ONLY_MODELS),
    _voice("Kiki", locale="zh-CN-tianjin", description="天津话女声音色。", supported_models=QWEN_TTS_FLASH_ONLY_MODELS),
)


def qwen_system_voice_names() -> frozenset[str]:
    return frozenset(item["voice"] for item in QWEN_SYSTEM_VOICES)


def qwen_system_voice_modes(voice_item: dict[str, Any]) -> list[str]:
    enabled_modes = voice_item.get("enabled_modes")
    if isinstance(enabled_modes, list):
        return [mode for mode in enabled_modes if mode in QWEN_SYSTEM_TTS_MODES]

    supported_models = voice_item.get("supported_models")
    if not isinstance(supported_models, list):
        return []

    supported_model_set = set(supported_models)
    modes: list[str] = []
    if supported_model_set & QWEN_API35_SYSTEM_TTS_STANDARD_MODEL_ALIASES:
        modes.append(QWEN_SYSTEM_TTS_MODE_STANDARD)
    if supported_model_set & QWEN_API35_SYSTEM_TTS_INSTRUCT_MODEL_ALIASES:
        modes.append(QWEN_SYSTEM_TTS_MODE_INSTRUCT)
    return modes


def qwen_published_system_voice_mode_map() -> dict[str, tuple[str, ...]]:
    return {
        str(item["voice"]): tuple(modes)
        for item in QWEN_SYSTEM_VOICES
        for modes in [qwen_system_voice_modes(item)]
        if modes
    }


def qwen_system_voice_available_in_api35(voice_item: dict[str, Any]) -> bool:
    return bool(qwen_system_voice_modes(voice_item))
