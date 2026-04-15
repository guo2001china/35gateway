from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response
from scalar_fastapi import Theme, get_scalar_api_reference
from starlette.requests import Request

from app.domains.site.discovery import build_llms_txt, build_robots_txt, build_sitemap_xml
from app.domains.site.info_pages import INFO_PAGE_ORDER, INFO_PAGES
from app.domains.site.renderers import (
    render_deploy_page,
    render_info_page,
    render_landing_page,
    render_models_page,
    render_topic_page,
)
from app.domains.site.topics import TOPIC_ORDER, TOPIC_PAGES


site_router = APIRouter()
DEFAULT_DOCS_FAVICON_URL = "/site-static/branding/favicon-32.png"


def get_scalar_api_reference_html(*, openapi_url: str, title: str) -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=openapi_url,
        title=title,
        scalar_proxy_url="https://proxy.scalar.com",
        scalar_favicon_url=DEFAULT_DOCS_FAVICON_URL,
        dark_mode=False,
        theme=Theme.DEFAULT,
        show_sidebar=True,
        hide_download_button=False,
    )


@site_router.get("/", include_in_schema=False)
async def landing_page(request: Request) -> HTMLResponse:
    return render_landing_page(request)


@site_router.get("/deploy", include_in_schema=False)
async def deploy_page(request: Request) -> HTMLResponse:
    return render_deploy_page(request)


@site_router.get("/models", include_in_schema=False)
async def models_page(request: Request) -> HTMLResponse:
    return render_models_page(request)


@site_router.get("/docs", include_in_schema=False)
async def scalar_docs(request: Request) -> HTMLResponse:
    return get_scalar_api_reference_html(
        openapi_url=request.app.openapi_url or "/openapi.json",
        title="35m.ai API Reference",
    )


@site_router.get("/robots.txt", include_in_schema=False)
async def robots_txt(request: Request) -> Response:
    return Response(content=build_robots_txt(request), media_type="text/plain")


@site_router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request) -> Response:
    return Response(content=build_sitemap_xml(request), media_type="application/xml")


@site_router.get("/llms.txt", include_in_schema=False)
@site_router.get("/.well-known/llms.txt", include_in_schema=False)
async def llms_txt(request: Request) -> Response:
    return Response(content=build_llms_txt(request), media_type="text/plain")


def _make_info_handler(page_key: str):
    async def info_page(request: Request) -> HTMLResponse:
        return render_info_page(request, page_key)

    return info_page


for page_key in INFO_PAGE_ORDER:
    slug = INFO_PAGES[page_key]["slug"]
    site_router.add_api_route(
        f"/{slug}",
        _make_info_handler(page_key),
        include_in_schema=False,
        methods=["GET"],
        name=f"site_info_{page_key}",
    )


def _make_topic_handler(topic_key: str):
    async def topic_page(request: Request) -> HTMLResponse:
        return render_topic_page(request, topic_key)

    return topic_page


for topic_key in TOPIC_ORDER:
    slug = TOPIC_PAGES[topic_key]["slug"]
    site_router.add_api_route(
        f"/{slug}",
        _make_topic_handler(topic_key),
        include_in_schema=False,
        methods=["GET"],
        name=f"site_topic_{topic_key}",
    )
