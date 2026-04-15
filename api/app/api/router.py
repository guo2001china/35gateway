from fastapi import APIRouter

from app.api.routes.auth import auth_router, console_router, files_router, me_router, redemption_router
from app.api.routes.models import (
    banana_router,
    catalog_router,
    estimates_router,
    google_gemini_router,
    kling_video_router,
    minimax_router,
    minimax_video_router,
    openai_chat_router,
    openai_responses_router,
    qwen_router,
    seedance_video_router,
    seedream_router,
    tasks_router,
    vidu_router,
    veo_router,
    wan_video_router,
)
from app.api.routes.system import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(health_router, tags=["health"], include_in_schema=False)
api_router.include_router(me_router, tags=["me"], include_in_schema=False)
api_router.include_router(redemption_router, tags=["me"], include_in_schema=False)
api_router.include_router(console_router, tags=["console"], include_in_schema=False)
api_router.include_router(files_router, tags=["files"])
api_router.include_router(catalog_router, tags=["catalog"])
api_router.include_router(estimates_router, tags=["estimates"])
api_router.include_router(banana_router, tags=["banana"])
api_router.include_router(seedance_video_router, tags=["seedance"])
api_router.include_router(seedream_router, tags=["seedream"])
api_router.include_router(google_gemini_router, tags=["google"])
api_router.include_router(kling_video_router, tags=["kling"])
api_router.include_router(minimax_router, tags=["minimax"])
api_router.include_router(minimax_video_router, tags=["minimax"])
api_router.include_router(openai_chat_router, tags=["openai"])
api_router.include_router(openai_responses_router, tags=["responses"])
api_router.include_router(qwen_router, tags=["qwen"])
api_router.include_router(tasks_router, tags=["tasks"])
api_router.include_router(vidu_router, tags=["vidu"])
api_router.include_router(veo_router, tags=["veo"])
api_router.include_router(wan_video_router, tags=["wan"])
