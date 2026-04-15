from __future__ import annotations

from fastapi import Request

from app.core.config import settings
from app.core.console_urls import resolve_console_base_url
from app.domains.site.info_pages import INFO_PAGE_ORDER, INFO_PAGES
from app.domains.site.topics import TOPIC_ORDER, TOPIC_PAGES


HTML_LANG = "zh-CN"
OG_LOCALE = "zh_CN"

CORE_PAGE_SLUGS = {
    "home": "",
    "models": "/models",
    "deploy": "/deploy",
    "docs": "/docs",
}
INFO_PAGE_SLUGS = {key: f"/{INFO_PAGES[key]['slug']}" for key in INFO_PAGE_ORDER}
TOPIC_PAGE_SLUGS = {key: f"/{TOPIC_PAGES[key]['slug']}" for key in TOPIC_ORDER}
PAGE_SLUGS = {**CORE_PAGE_SLUGS, **INFO_PAGE_SLUGS, **TOPIC_PAGE_SLUGS}


def site_origin(request: Request) -> str:
    configured = settings.site_url.strip().rstrip("/")
    if configured:
        return configured
    return str(request.base_url).rstrip("/")


def console_origin(request: Request) -> str:
    return resolve_console_base_url(request)


def localized_path(page_key: str) -> str:
    slug = PAGE_SLUGS[page_key]
    return slug or "/"


def absolute_url(origin: str, path: str) -> str:
    if path == "/":
        return f"{origin}/"
    return f"{origin}{path}"


def route_href(route_key: str) -> str:
    if route_key == "docs":
        return "/docs"
    if route_key == "pricing":
        return localized_path("models")
    return localized_path(route_key)


def nav_items() -> list[dict[str, object]]:
    return [
        {"key": "home", "label": "首页", "href": localized_path("home"), "primary": False},
        {"key": "models", "label": "模型", "href": localized_path("models"), "primary": False},
        # {"key": "pricing", "label": "价格", "href": route_href("pricing"), "primary": False},
        {"key": "deploy", "label": "部署", "href": localized_path("deploy"), "primary": False},
        {"key": "console", "label": "控制台", "href": "/console/login", "primary": False, "console_entry": True},
        {"key": "docs", "label": "API 文档", "href": "/docs", "primary": True},
    ]


def site_labels() -> dict[str, object]:
    return {
        "footer_title": "35m.ai",
        "footer_description": "99.99大模型，适合API对接、自托管、代理部署、定制集成的团队",
        "footer_note": "© 2026 35m.ai",
    }


def footer_community_items() -> list[dict[str, str]]:
    return [
        {"label": "微信群", "kind": "二维码待补"},
        {"label": "TG 群", "kind": "二维码待补"},
        {"label": "Discord", "kind": "链接待补"},
    ]


def footer_groups() -> list[dict[str, object]]:
    return [
        {
            "title": "产品",
            "links": [
                {"label": "模型", "href": route_href("models")},
                {"label": "价格", "href": route_href("models")},
                {"label": "部署", "href": route_href("deploy")},
                {"label": "API 文档", "href": route_href("docs")},
            ],
        },
        {
            "title": "支持",
            "links": [
                {"label": "帮助支持", "href": route_href("support")},
            ],
        },
        {
            "title": "公司",
            "links": [
                {"label": "35m.ai", "href": route_href("about")},
                {"label": "商务合作", "href": route_href("contact")},
            ],
        },
        {
            "title": "条款",
            "links": [
                {"label": "隐私政策", "href": route_href("privacy")},
                {"label": "使用条款", "href": route_href("terms")},
                {"label": "数据与日志", "href": route_href("data-logging")},
            ],
        },
    ]


def is_topic_page(page_key: str) -> bool:
    return page_key in TOPIC_PAGES
