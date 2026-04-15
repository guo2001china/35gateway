from __future__ import annotations

from fastapi import Request

from app.domains.site.info_pages import INFO_PAGE_ORDER, INFO_PAGES
from app.domains.site.navigation import PAGE_SLUGS, absolute_url, localized_path, site_origin
from app.domains.site.topics import TOPIC_ORDER, TOPIC_PAGES


def build_robots_txt(request: Request) -> str:
    origin = site_origin(request)
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {origin}/sitemap.xml",
            "",
        ]
    )


def build_sitemap_xml(request: Request) -> str:
    origin = site_origin(request)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page_key in PAGE_SLUGS:
        lines.append("  <url>")
        lines.append(f"    <loc>{absolute_url(origin, localized_path(page_key))}</loc>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def build_llms_txt(request: Request) -> str:
    origin = site_origin(request)
    answer_lines = []
    for topic_key in TOPIC_ORDER:
        slug = TOPIC_PAGES[topic_key]["slug"]
        title = TOPIC_PAGES[topic_key]["card_title"]
        answer_lines.append(f"- {title}: {origin}/{slug}")
    info_lines = []
    for page_key in INFO_PAGE_ORDER:
        slug = INFO_PAGES[page_key]["slug"]
        title = INFO_PAGES[page_key]["page_title"]
        info_lines.append(f"- {title}: {origin}/{slug}")
    return "\n".join(
        [
            "# 35m.ai ",
            "",
            "> OpenAI-compatible 模型接入层，统一接入文本、图片、视频模型。",
            "",
            "## Core facts",
            "- 一个入口统一接入文本、图片、视频模型。",
            "- 请求完成后仍可查看价格、成功率和耗时。",
            "- 支持请求前预计费，先估算再创建高成本请求。",
            "- 支持 API 对接、自托管、代理部署和定制集成。",
            "",
            "## Human-readable pages",
            f"- 首页: {origin}/",
            f"- 模型与价格: {origin}/models",
            f"- 部署: {origin}/deploy",
            "",
            "## Trust and policy pages",
            *info_lines,
            "",
            "## Answer pages",
            *answer_lines,
            "",
            "## API and machine-readable endpoints",
            f"- Docs: {origin}/docs",
            f"- OpenAPI schema: {origin}/openapi.json",
            f"- Public model catalog: {origin}/v1/models",
            "",
        ]
    )
