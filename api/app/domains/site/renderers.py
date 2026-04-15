from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.console_urls import resolve_console_url
from app.db.session import SessionLocal
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot
from app.domains.site.content import (
    deploy_content,
    group_models,
    home_content,
    info_page_content,
    models_content,
    topic_page_content,
)
from app.domains.site.doc_links import model_api_doc_href
from app.domains.site.navigation import (
    HTML_LANG,
    OG_LOCALE,
    absolute_url,
    footer_community_items,
    footer_groups,
    is_topic_page,
    localized_path,
    nav_items,
    site_labels,
    site_origin,
)
from app.domains.platform.services.model_catalog_service import ModelCatalogService


SITE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(SITE_DIR / "templates"))

OFFICIAL_PROVIDER_CODES = {
    "openai_official",
    "deepseek_official",
    "google_official",
    "google_veo3",
}

DEFAULT_SITE_NAME = "35m.ai"
DEFAULT_SITE_SLOGAN = "你的私人算力中心"
DEFAULT_SITE_LOGO_URL = "/site-static/branding/logo-nav.png"
DEFAULT_SITE_FAVICON_URL = "/site-static/branding/favicon-32.png"
DEFAULT_SITE_APPLE_TOUCH_ICON_URL = "/site-static/branding/apple-touch-icon.png"


def _breadcrumb_items(page_key: str, page_title: str) -> list[dict[str, str]]:
    if page_key == "home":
        return [{"name": "35m.ai", "path": localized_path("home")}]
    return [
        {"name": "首页", "path": localized_path("home")},
        {"name": page_title, "path": localized_path(page_key)},
    ]


def _structured_data(
    *,
    origin: str,
    page_key: str,
    page_title: str,
    page_description: str,
    page_url: str,
    page_payload: dict[str, object] | None = None,
) -> list[str]:
    lang = HTML_LANG
    schemas: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "35m.ai",
            "url": origin,
            "description": "OpenAI-compatible 模型接入层。",
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page_title,
            "description": page_description,
            "url": page_url,
            "inLanguage": lang,
        },
    ]
    if page_key == "home":
        schemas.extend(
            [
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "35m.ai",
                    "url": origin,
                    "inLanguage": lang,
                },
                {
                    "@context": "https://schema.org",
                    "@type": "SoftwareApplication",
                    "name": "35m.ai",
                    "applicationCategory": "DeveloperApplication",
                    "operatingSystem": "Web",
                    "url": page_url,
                    "description": page_description,
                    "featureList": [
                        "统一接入文本、图片、视频模型",
                        "支持调用前预计费估算",
                        "价格、成功率、耗时可见",
                        "支持托管与自托管部署",
                    ],
                },
            ]
        )
    else:
        breadcrumb_items = _breadcrumb_items(page_key, page_title)
        item_list = []
        for idx, item in enumerate(breadcrumb_items, start=1):
            item_list.append(
                {
                    "@type": "ListItem",
                    "position": idx,
                    "name": item["name"],
                    "item": absolute_url(origin, item["path"]),
                }
            )
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": item_list,
            }
        )
        if is_topic_page(page_key) and page_payload is not None:
            schemas.append(
                {
                    "@context": "https://schema.org",
                    "@type": "TechArticle",
                    "headline": page_title,
                    "description": page_description,
                    "url": page_url,
                    "inLanguage": lang,
                    "mainEntityOfPage": page_url,
                }
            )
            faq_items = []
            for item in page_payload.get("faq", []):
                faq_items.append(
                    {
                        "@type": "Question",
                        "name": str(item["q"]),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": str(item["a"]),
                        },
                    }
                )
            if faq_items:
                schemas.append(
                    {
                        "@context": "https://schema.org",
                        "@type": "FAQPage",
                        "mainEntity": faq_items,
                    }
                )
    return [json.dumps(item, ensure_ascii=False) for item in schemas]


def _page_shell_context(
    *,
    request: Request,
    page_key: str,
    page_title: str,
    page_description: str,
    page_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    origin = site_origin(request)
    current_path = localized_path(page_key)
    current_url = absolute_url(origin, current_path)
    shell_nav_links = nav_items()
    for item in shell_nav_links:
        if item.get("console_entry"):
            item["href"] = resolve_console_url(request, "/login")
    labels = site_labels()
    brand_logo_url = DEFAULT_SITE_LOGO_URL
    brand_favicon_url = DEFAULT_SITE_FAVICON_URL
    brand_apple_touch_icon_url = DEFAULT_SITE_APPLE_TOUCH_ICON_URL
    brand_slogan = DEFAULT_SITE_SLOGAN
    brand_has_custom_slogan = False
    brand_site_name = DEFAULT_SITE_NAME
    brand_display_text = f"{DEFAULT_SITE_NAME} | {brand_slogan}"
    resolved_page_title = page_title.strip()

    return {
        "html_lang": HTML_LANG,
        "og_locale": OG_LOCALE,
        "page_title": resolved_page_title,
        "page_description": page_description,
        "og_title": resolved_page_title,
        "og_description": page_description,
        "canonical_url": current_url,
        "brand_logo_url": brand_logo_url,
        "brand_favicon_url": brand_favicon_url,
        "brand_apple_touch_icon_url": brand_apple_touch_icon_url,
        "brand_site_name": brand_site_name,
        "brand_slogan": brand_slogan,
        "brand_has_custom_slogan": brand_has_custom_slogan,
        "brand_display_text": brand_display_text,
        "nav_links": [{**item, "active": item["key"] == page_key} for item in shell_nav_links],
        "console_home_url": resolve_console_url(request, "/"),
        "console_login_url": resolve_console_url(request, "/login"),
        "footer_groups": footer_groups(),
        "footer_community": footer_community_items(),
        "active_page": page_key,
        "footer_title": labels["footer_title"],
        "footer_description": labels["footer_description"],
        "footer_note": labels["footer_note"],
        "structured_data_blocks": _structured_data(
            origin=origin,
            page_key=page_key,
            page_title=page_title,
            page_description=page_description,
            page_url=current_url,
            page_payload=page_payload,
        ),
    }


def _resolve_console_entry_actions(
    actions: list[dict[str, object]],
    *,
    console_login_url: str,
) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for action in actions:
        item = dict(action)
        if item.get("console_entry"):
            item["href"] = console_login_url
        resolved.append(item)
    return resolved


def _is_official_provider(provider_code: str) -> bool:
    return provider_code in OFFICIAL_PROVIDER_CODES or provider_code.endswith("_official")


def _format_latency(p50_ms: float | None) -> str:
    if p50_ms is None:
        return "待验证"
    if p50_ms >= 1000:
        return f"{round(p50_ms / 1000, 1):.1f}s"
    return f"{int(round(p50_ms))}ms"


def _format_success_rate(success_rate: float | None, sample_count: int) -> str:
    if success_rate is None:
        return "待验证"
    if sample_count < 20:
        return f"{success_rate:.1f}%*"
    return f"{success_rate:.1f}%"


def _format_price_summary(pricing: dict[str, object]) -> str:
    currency = str(pricing.get("currency") or "CNY")
    sale_price = pricing.get("sale_price_fields") or pricing.get("official_price") or {}
    unit_map = {"token": "/ 1M", "image": "/ 图", "second": "/ 秒"}
    if not isinstance(sale_price, dict):
        return "—"
    prioritized_keys = [
        "input_per_1m_tokens",
        "cache_miss_input_per_1m_tokens",
        "output_per_image",
        "per_second",
        "output_per_1m_tokens",
    ]
    for key in prioritized_keys:
        value = sale_price.get(key)
        if value:
            unit = "token"
            if key == "output_per_image":
                unit = "image"
            elif key == "per_second":
                unit = "second"
            prefix = "¥" if currency.upper() == "CNY" else f"{currency} "
            return f"{prefix}{value} {unit_map[unit]}".replace("  ", " ").strip()
    return "—"


def _provider_badges(providers: list[dict[str, object]]) -> list[dict[str, object]]:
    non_official = [item for item in providers if not _is_official_provider(str(item["provider_code"]))]
    official = [item for item in providers if _is_official_provider(str(item["provider_code"]))]
    selected = non_official[:2]
    if official:
        selected.append(official[0])
    elif len(non_official) > 2:
        selected.append(non_official[2])

    badges: list[dict[str, object]] = []
    vendor_index = 0
    for item in selected:
        provider_code = str(item["provider_code"])
        metrics = dict(item.get("metrics") or {})
        latency = dict(metrics.get("latency") or {})
        if _is_official_provider(provider_code):
            label = "官网保底"
            variant = "official"
        else:
            label = f"供应商{chr(65 + vendor_index)}"
            vendor_index += 1
            variant = "vendor"
        badges.append(
            {
                "label": label,
                "variant": variant,
                "success_rate": _format_success_rate(metrics.get("success_rate"), int(metrics.get("sample_count") or 0)),
                "latency": _format_latency(latency.get("p50_ms")),
            }
        )
    return badges


def _build_model_card_details(model_codes: list[str]) -> dict[str, dict[str, object]]:
    snapshot = get_platform_config_snapshot()
    pricing_index = {
        model_code: {
            "currency": pricing.currency,
            "sale_price_fields": pricing.sale_price_fields,
            "official_price": pricing.official_price,
        }
        for model_code in model_codes
        if (pricing := snapshot.get_pricing_for_model(model_code)) is not None
    }
    details: dict[str, dict[str, object]] = {}
    with SessionLocal() as db:
        catalog = ModelCatalogService(db)
        for model_code in model_codes:
            providers = catalog.list_model_providers(model_code, window="24h")
            badges = _provider_badges(providers)
            details[model_code] = {
                "price_summary": _format_price_summary(pricing_index.get(model_code, {})),
                "provider_badges": badges,
            }
    return details


def _deploy_biz_contact() -> dict[str, object]:
    contact_value = settings.site_biz_contact_value.strip()
    configured_label = settings.site_biz_contact_label.strip()
    contact_label = configured_label or "微信号"
    return {
        "qr_url": settings.site_biz_qr_url.strip(),
        "contact_label": contact_label,
        "contact_value": contact_value,
        "has_qr": bool(settings.site_biz_qr_url.strip()),
        "has_contact": bool(contact_value),
    }


def render_landing_page(request: Request):
    page = home_content()
    shell = _page_shell_context(
        request=request,
        page_key="home",
        page_title=str(page["page_title"]),
        page_description=str(page["page_description"]),
        page_payload=page,
    )
    page = {
        **page,
        "hero_actions": _resolve_console_entry_actions(
            list(page["hero_actions"]),
            console_login_url=str(shell["console_login_url"]),
        ),
    }
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            **shell,
            "page": page,
        },
    )

def render_deploy_page(request: Request):
    page = deploy_content()
    return templates.TemplateResponse(
        request=request,
        name="deploy.html",
        context={
            **_page_shell_context(
                request=request,
                page_key="deploy",
                page_title=str(page["page_title"]),
                page_description=str(page["page_description"]),
                page_payload=page,
            ),
            "page": page,
            "biz_contact": _deploy_biz_contact(),
        },
    )


def render_models_page(request: Request):
    groups = group_models()
    model_codes = [item["model_code"] for items in groups.values() for item in items]
    card_details = _build_model_card_details(model_codes)
    for category_items in groups.values():
        for item in category_items:
            detail = card_details.get(item["model_code"], {})
            item["price_summary"] = detail.get("price_summary", "—")
            item["provider_badges"] = detail.get("provider_badges", [])
            item["api_doc_href"] = model_api_doc_href(
                model_code=str(item["model_code"]),
                route_group=str(item["route_group"]),
            )
    catalog_page = models_content()
    page = {
        **catalog_page,
        "page_title": "35m.ai | 模型总览",
        "page_description": "35m.ai 模型与价格总页：统一展示文本、图片、视频模型的公开模型名、路由组、调用入口和价格口径。",
    }
    return templates.TemplateResponse(
        request=request,
        name="models.html",
        context={
            **_page_shell_context(
                request=request,
                page_key="models",
                page_title=str(page["page_title"]),
                page_description=str(page["page_description"]),
                page_payload=page,
            ),
            "page": page,
            "model_groups": groups,
        },
    )


def render_info_page(request: Request, page_key: str):
    page = info_page_content(page_key)
    extra_context: dict[str, object] = {}
    if page_key == "contact":
        extra_context["biz_contact"] = _deploy_biz_contact()
    return templates.TemplateResponse(
        request=request,
        name="info.html",
        context={
            **_page_shell_context(
                request=request,
                page_key=page_key,
                page_title=str(page["page_title"]),
                page_description=str(page["page_description"]),
                page_payload=page,
            ),
            "page": page,
            **extra_context,
        },
    )


def render_topic_page(request: Request, topic_key: str):
    page = topic_page_content(topic_key)
    return templates.TemplateResponse(
        request=request,
        name="answer.html",
        context={
            **_page_shell_context(
                request=request,
                page_key=topic_key,
                page_title=str(page["page_title"]),
                page_description=str(page["page_description"]),
                page_payload=page,
            ),
            "page": page,
        },
    )
