from __future__ import annotations

import re


def scalar_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "index"


def scalar_tag_slug(tag_name: str) -> str:
    return scalar_slug(tag_name)


def scalar_operation_slug(*, method: str, path: str) -> str:
    return scalar_slug(f"{method}-{path}")


def scalar_operation_href(*, tag_name: str, method: str, path: str) -> str:
    return f"/docs#tag/{scalar_tag_slug(tag_name)}/{scalar_operation_slug(method=method, path=path)}"


def model_api_doc_href(*, model_code: str, route_group: str) -> str:
    route_group = route_group.strip()
    if route_group == "openai":
        return scalar_operation_href(tag_name="openai", method="post", path="/v1/chat/completions")
    if route_group == "responses":
        return scalar_operation_href(tag_name="responses", method="post", path="/v1/responses")
    if route_group == "gemini":
        return scalar_operation_href(
            tag_name="google",
            method="post",
            path="/google/v1beta/models/{model}:generateContent",
        )
    if route_group == "banana":
        return scalar_operation_href(tag_name="banana", method="post", path=f"/v1/{model_code}")
    if route_group == "seedance":
        return scalar_operation_href(tag_name="seedance", method="post", path=f"/v1/{model_code}")
    if route_group == "seedream":
        return scalar_operation_href(tag_name="seedream", method="post", path=f"/v1/{model_code}")
    if route_group == "wan_video":
        return scalar_operation_href(tag_name="wan", method="post", path=f"/v1/{model_code}")
    if route_group == "minimax_video":
        return scalar_operation_href(tag_name="minimax", method="post", path=f"/v1/{model_code}")
    if route_group == "veo3":
        if model_code == "veo-3":
            return scalar_operation_href(tag_name="veo", method="post", path="/v1/veo-3")
        if model_code == "veo-3-fast":
            return scalar_operation_href(tag_name="veo", method="post", path="/v1/veo-3-fast")
    if route_group == "veo31":
        if model_code == "veo-3.1":
            return scalar_operation_href(tag_name="veo", method="post", path="/v1/veo-3.1")
        if model_code == "veo-3.1-fast":
            return scalar_operation_href(tag_name="veo", method="post", path="/v1/veo-3.1-fast")
    return "/docs"
