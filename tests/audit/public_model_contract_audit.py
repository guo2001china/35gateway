#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = REPO_ROOT / "api" / "app" / "domains" / "platform" / "services" / "platform_bootstrap_data.json"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "output" / "playwright" / "public-model-contract-audit.json"

CHAT_MODELS = {
    "DeepSeek-V3.2",
    "MiniMax-M2.7",
    "MiniMax-M2.7-highspeed",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
    "glm-4.7-flash",
    "gpt-5",
    "gpt-5.2",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "openrouter-free",
    "step-3.5-flash",
}

EXPECTED_PARAMS: dict[tuple[str, str], list[str]] = {
    **{(model_code, "openai"): ["model", "messages", "stream"] for model_code in CHAT_MODELS},
    ("gemini-2.5-pro", "gemini"): ["model", "contents", "generationConfig"],
    ("gemini-2.5-pro", "openai"): ["model", "messages", "stream"],
    ("gpt-5.4-pro", "responses"): ["model", "input", "instructions", "stream"],
    ("doubao-seedream-4.5", "seedream"): ["prompt", "image", "size", "response_format", "stream", "watermark"],
    (
        "doubao-seedream-5.0-lite",
        "seedream",
    ): [
        "prompt",
        "image",
        "size",
        "response_format",
        "stream",
        "watermark",
        "output_format",
        "tools",
        "sequential_image_generation",
        "sequential_image_generation_options",
        "optimize_prompt_options",
    ],
    ("seedance-2.0", "seedance"): [
        "prompt",
        "input_reference",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "seed",
    ],
    ("seedance-2.0-fast", "seedance"): [
        "prompt",
        "input_reference",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "seed",
    ],
    ("nano-banana", "banana"): ["prompt", "image_urls", "aspect_ratio", "resolution"],
    ("nano-banana-pro", "banana"): ["prompt", "image_urls", "aspect_ratio", "resolution"],
    ("nano-banana-2", "banana"): ["prompt", "image_urls", "aspect_ratio", "resolution"],
    ("qwen-voice-enrollment", "qwen_voice_clone"): ["name", "audio_url", "text", "language"],
    ("qwen3-tts-flash", "qwen_tts"): ["text", "voice", "language_type"],
    ("qwen3-tts-instruct-flash", "qwen_tts"): ["text", "voice", "mode", "language_type", "instructions", "optimize_instructions"],
    ("qwen3-tts-vc-2026-01-22", "qwen_tts"): ["text", "voice", "language_type"],
    ("speech-2.8-hd", "minimax_t2a_async"): [
        "text",
        "text_file_id",
        "voice_id",
        "voice_setting",
        "audio_setting",
        "language_boost",
        "pronunciation_dict",
        "subtitle_enable",
    ],
    ("speech-2.8-turbo", "minimax_t2a_async"): [
        "model",
        "text",
        "text_file_id",
        "voice_id",
        "voice_setting",
        "audio_setting",
        "language_boost",
        "pronunciation_dict",
        "subtitle_enable",
    ],
    ("veo-3", "veo3"): [
        "prompt",
        "input_reference",
        "first_frame",
        "last_frame",
        "reference_images",
        "video_url",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "number_of_videos",
        "person_generation",
        "negative_prompt",
        "seed",
    ],
    ("veo-3-fast", "veo3"): [
        "prompt",
        "input_reference",
        "first_frame",
        "last_frame",
        "reference_images",
        "video_url",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "number_of_videos",
        "person_generation",
        "negative_prompt",
        "seed",
    ],
    ("veo-3.1", "veo31"): [
        "prompt",
        "input_reference",
        "first_frame",
        "last_frame",
        "reference_images",
        "video_url",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "number_of_videos",
        "person_generation",
        "negative_prompt",
        "seed",
    ],
    ("veo-3.1-fast", "veo31"): [
        "prompt",
        "input_reference",
        "first_frame",
        "last_frame",
        "reference_images",
        "video_url",
        "resolution",
        "aspect_ratio",
        "seconds",
        "generate_audio",
        "number_of_videos",
        "person_generation",
        "negative_prompt",
        "seed",
    ],
    ("wan2.6", "wan_video"): [
        "prompt",
        "input_reference",
        "reference_urls",
        "audio_url",
        "negative_prompt",
        "size",
        "resolution",
        "aspect_ratio",
        "seconds",
        "prompt_extend",
        "generate_audio",
        "watermark",
        "shot_type",
    ],
    ("wan2.6-flash", "wan_video"): [
        "prompt",
        "input_reference",
        "reference_urls",
        "audio_url",
        "negative_prompt",
        "generate_audio",
        "size",
        "resolution",
        "aspect_ratio",
        "seconds",
        "prompt_extend",
        "watermark",
        "shot_type",
    ],
    ("minimax-hailuo-02", "minimax_video"): [
        "prompt",
        "input_reference",
        "first_frame",
        "last_frame",
        "resolution",
        "aspect_ratio",
        "seconds",
        "prompt_optimizer",
        "fast_pretreatment",
    ],
    ("minimax-hailuo-2.3", "minimax_video"): [
        "prompt",
        "input_reference",
        "resolution",
        "aspect_ratio",
        "seconds",
        "prompt_optimizer",
        "fast_pretreatment",
    ],
    ("minimax-hailuo-2.3-fast", "minimax_video"): [
        "prompt",
        "input_reference",
        "resolution",
        "aspect_ratio",
        "seconds",
        "prompt_optimizer",
        "fast_pretreatment",
    ],
    ("kling-o1", "kling_video"): [
        "prompt",
        "input_reference",
        "reference_images",
        "video_url",
        "first_frame",
        "last_frame",
        "mode",
        "aspect_ratio",
        "seconds",
        "watermark",
    ],
    ("viduq3-pro", "vidu"): ["mode", "prompt", "images", "duration", "resolution", "audio", "off_peak", "is_rec"],
    ("viduq3-turbo", "vidu"): ["mode", "prompt", "images", "duration", "resolution", "audio", "off_peak", "is_rec"],
}


@dataclass
class AuditRow:
    model_code: str
    route_group: str
    endpoint: str | None
    expected: list[str]
    actual: list[str]
    missing: list[str]
    extra: list[str]
    status: str


def main() -> int:
    payload = json.loads(BOOTSTRAP_PATH.read_text(encoding="utf-8"))
    rows: list[AuditRow] = []
    errors: list[str] = []

    for route in payload["routes"]:
        if not route.get("public_api_visible"):
            continue
        model_code = str(route["model_code"])
        route_group = str(route["route_group"])
        actual = [item["name"] for item in (route.get("api_doc_json") or {}).get("parameters") or []]
        expected = EXPECTED_PARAMS.get((model_code, route_group))
        if expected is None:
            errors.append(f"missing expected contract for public model {(model_code, route_group)!r}")
            continue
        missing = [name for name in expected if name not in actual]
        extra = [name for name in actual if name not in expected]
        rows.append(
            AuditRow(
                model_code=model_code,
                route_group=route_group,
                endpoint=(route.get("endpoints_json") or {}).get("create"),
                expected=expected,
                actual=actual,
                missing=missing,
                extra=extra,
                status="passed" if not missing and not extra else "failed",
            )
        )

    summary = {
        "total_public_models": len(rows),
        "passed": sum(1 for row in rows if row.status == "passed"),
        "failed": sum(1 for row in rows if row.status == "failed"),
        "errors": errors,
        "rows": [asdict(row) for row in sorted(rows, key=lambda row: row.model_code.lower())],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed"] or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
