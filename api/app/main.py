import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.router import api_router
from app.core.config import settings
from app.core.console_urls import resolve_console_url
from app.core.request_id import generate_request_id
from app.db.init_db import close_app_db, init_app_db
from app.domains.site.renderers import SITE_DIR
from app.domains.platform.services.platform_config_snapshot import reload_platform_config_snapshot
from app.domains.site.router import site_router

logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST_DIR = PROJECT_ROOT / "web" / "dist"
WEB_CONSOLE_ASSETS_DIR = WEB_DIST_DIR / "assets"
WEB_CONSOLE_INDEX_FILE = WEB_DIST_DIR / "index.html"

OPENAPI_TAGS = [
    {"name": "auth", "description": "用户认证与登录相关接口。"},
    {"name": "catalog", "description": "模型目录、供应商对比与公开查询接口。"},
    {"name": "estimates", "description": "统一预计费测算接口，按公开模型契约返回价格、算力与供应商排序。"},
    {"name": "openai", "description": "文本模型接口，当前主要为 OpenAI 兼容 chat completion。"},
    {"name": "responses", "description": "OpenAI Responses API 文本接口。"},
    {"name": "minimax", "description": "MiniMax 语音合成、快速克隆与 Hailuo 视频生成接口。"},
    {"name": "qwen", "description": "Qwen provider-scoped 语音合成与声音克隆接口。"},
    {"name": "google", "description": "Google Gemini 文本模型接口。"},
    {"name": "kling", "description": "Kling 视频生成接口，当前公开模型码为 kling-o1。"},
    {"name": "banana", "description": "Nano Banana 系列图片生成与编辑接口。"},
    {"name": "seedance", "description": "Seedance 2.0 视频生成接口，当前公开模型码使用 seedance-2.0 / seedance-2.0-fast。"},
    {"name": "seedream", "description": "Doubao Seedream 系列图片生成接口。"},
    {"name": "vidu", "description": "Vidu Q3 视频生成接口，公开模型码使用 viduq3-pro / viduq3-turbo。"},
    {"name": "veo", "description": "Veo 视频生成接口，公开模型码使用 veo-3 / veo-3.1。"},
    {"name": "wan", "description": "Wan 2.6 视频生成接口，公开模型码使用 wan2.6 / wan2.6-flash。"},
    {"name": "tasks", "description": "统一异步任务查询与内容下载接口。"},
]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-API35-Request-Id") or generate_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-API35-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_db()
    reload_platform_config_snapshot()
    yield
    await close_app_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="35gateway",
        version="0.1.0",
        description=(
            "35gateway console backend. "
            "使用 `/docs` 查看 Scalar 交互文档，使用 `/openapi.json` 获取原始 OpenAPI schema。"
        ),
        docs_url=None,
        redoc_url=None,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    if settings.cors_allowed_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins_list,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-API35-Request-Id"],
        )
    app.add_middleware(RequestIdMiddleware)
    app.mount("/site-static", StaticFiles(directory=str(SITE_DIR / "static")), name="site_static")

    if WEB_CONSOLE_ASSETS_DIR.exists():
        app.mount("/console/assets", StaticFiles(directory=str(WEB_CONSOLE_ASSETS_DIR)), name="console_assets")

    def _console_response(request: Request, path: str = "/") -> Response:
        if WEB_CONSOLE_INDEX_FILE.exists():
            return FileResponse(WEB_CONSOLE_INDEX_FILE)
        console_target = resolve_console_url(request, path)
        if console_target.startswith(("http://", "https://")):
            return RedirectResponse(console_target, status_code=307)
        raise HTTPException(status_code=404, detail="console_frontend_not_built")

    @app.get("/console", include_in_schema=False, response_model=None)
    async def console_entry(request: Request) -> Response:
        return _console_response(request, "/")

    @app.get("/console/", include_in_schema=False, response_model=None)
    async def console_entry_slash(request: Request) -> Response:
        return _console_response(request, "/")

    @app.get("/console/{path:path}", include_in_schema=False, response_model=None)
    async def console_spa(request: Request, path: str) -> Response:
        return _console_response(request, f"/{path}")

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(site_router)
    return app


app = create_app()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def run(*, reload: bool | None = None) -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8025,
        reload=_env_flag("API35_RELOAD", True) if reload is None else reload,
    )


def run_stable() -> None:
    run(reload=False)


if __name__ == "__main__":
    run()
