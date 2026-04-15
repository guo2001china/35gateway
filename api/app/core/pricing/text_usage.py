from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

DEFAULT_ESTIMATED_OUTPUT_TOKENS = 1024
ESTIMATED_CHARS_PER_TOKEN = 4
_TEXT_PART_TYPES = {"text", "input_text", "output_text"}


@dataclass(frozen=True)
class TextUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0
    usage_source: str = "estimated"
    pricing_tier: str | None = None


def _collect_openai_content_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []

    values: list[str] = []
    for item in value:
        if isinstance(item, str):
            values.append(item)
            continue
        if not isinstance(item, dict):
            continue
        part_type = str(item.get("type") or "").strip().lower()
        text = item.get("text")
        if isinstance(text, str) and (not part_type or part_type in _TEXT_PART_TYPES):
            values.append(text)
    return values


def _collect_openai_message_texts(messages: Any) -> list[str]:
    if not isinstance(messages, list):
        return []

    values: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        values.extend(_collect_openai_content_texts(item.get("content")))
    return values


def _collect_responses_input_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_collect_responses_input_texts(item))
        return values
    if not isinstance(value, dict):
        return []

    values: list[str] = []
    part_type = str(value.get("type") or "").strip().lower()
    text = value.get("text")
    if isinstance(text, str) and (not part_type or part_type in _TEXT_PART_TYPES):
        values.append(text)
    input_text = value.get("input_text")
    if isinstance(input_text, str):
        values.append(input_text)
    content = value.get("content")
    if isinstance(content, list):
        for item in content:
            values.extend(_collect_responses_input_texts(item))
    elif isinstance(content, str) and part_type in {"message", "text", "input_text"}:
        values.append(content)
    return values


def _collect_gemini_content_texts(contents: Any) -> list[str]:
    if not isinstance(contents, list):
        return []

    values: list[str] = []
    for item in contents:
        if not isinstance(item, dict):
            continue
        parts = item.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                values.append(text)
    return values


def estimate_text_usage(*, route_group: str, payload: dict[str, Any]) -> TextUsage:
    input_tokens = _estimate_input_tokens(route_group=route_group, payload=payload)
    output_tokens = _estimate_output_tokens(route_group=route_group, payload=payload)
    total_tokens = input_tokens + output_tokens
    return TextUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=0,
        usage_source="estimated",
    )


def parse_text_usage_from_response(*, route_group: str, response_payload: dict[str, Any]) -> TextUsage | None:
    if route_group == "gemini":
        usage = response_payload.get("usageMetadata")
        if not isinstance(usage, dict):
            return None
        try:
            input_tokens = int(usage.get("promptTokenCount") or 0)
            output_tokens = int(usage.get("candidatesTokenCount") or 0)
        except (TypeError, ValueError):
            return None
        total_raw = usage.get("totalTokenCount")
        try:
            total_tokens = int(total_raw) if total_raw is not None else input_tokens + output_tokens
        except (TypeError, ValueError):
            total_tokens = input_tokens + output_tokens
        return TextUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_input_tokens=0,
            usage_source="provider_usage",
        )

    usage = response_payload.get("usage")
    if not isinstance(usage, dict):
        return None

    input_field = "input_tokens" if route_group == "responses" else "prompt_tokens"
    output_field = "output_tokens" if route_group == "responses" else "completion_tokens"
    try:
        input_tokens = int(usage.get(input_field) or 0)
        output_tokens = int(usage.get(output_field) or 0)
    except (TypeError, ValueError):
        return None
    total_raw = usage.get("total_tokens")
    try:
        total_tokens = int(total_raw) if total_raw is not None else input_tokens + output_tokens
    except (TypeError, ValueError):
        total_tokens = input_tokens + output_tokens
    return TextUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=_cached_input_tokens_from_usage(usage),
        usage_source="provider_usage",
    )


def _estimate_input_tokens(*, route_group: str, payload: dict[str, Any]) -> int:
    if route_group == "openai":
        text_values = _collect_openai_message_texts(payload.get("messages") or [])
    elif route_group == "responses":
        text_values = _collect_responses_input_texts(payload.get("input"))
        instructions = payload.get("instructions")
        if isinstance(instructions, str):
            text_values.append(instructions)
    elif route_group == "gemini":
        text_values = _collect_gemini_content_texts(payload.get("contents") or [])
    else:
        text_values = []
    total_chars = sum(len(item) for item in text_values if item)
    if total_chars <= 0:
        return 0
    return max(1, math.ceil(total_chars / ESTIMATED_CHARS_PER_TOKEN))


def _estimate_output_tokens(*, route_group: str, payload: dict[str, Any]) -> int:
    if route_group == "openai":
        raw = payload.get("max_tokens")
    elif route_group == "responses":
        raw = payload.get("max_output_tokens")
    elif route_group == "gemini":
        raw = (payload.get("generationConfig") or {}).get("maxOutputTokens")
    else:
        raw = None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_ESTIMATED_OUTPUT_TOKENS
    return max(1, parsed)


def _cached_input_tokens_from_usage(usage: dict[str, Any] | None) -> int:
    if not isinstance(usage, dict):
        return 0
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        try:
            return max(0, int(prompt_details.get("cached_tokens") or 0))
        except (TypeError, ValueError):
            return 0
    input_details = usage.get("input_tokens_details")
    if isinstance(input_details, dict):
        try:
            return max(0, int(input_details.get("cached_tokens") or 0))
        except (TypeError, ValueError):
            return 0
    try:
        return max(0, int(usage.get("cached_input_tokens") or 0))
    except (TypeError, ValueError):
        return 0
