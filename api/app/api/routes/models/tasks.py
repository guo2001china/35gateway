from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import ApiKeyContext, require_api_key
from app.api.deps import get_db
from app.api.openapi_responses import AUTH_ERROR_RESPONSES, TASK_NOT_FOUND_RESPONSE
from app.api.schemas import VideoTaskResponse
from app.domains.platform.entities.entities import Request as RequestLog
from app.domains.platform.entities.entities import Task
from app.domains.platform.services.async_task_execution import AsyncTaskExecutionService

router = APIRouter()


# 统一任务查询会按用户归属做过滤，避免跨账户读取任务。
def _get_task_with_route_group(db: Session, platform_task_id: str, user_id: int) -> tuple[Task, str]:
    row = (
        db.query(Task)
        .join(RequestLog, Task.request_id == RequestLog.id)
        .filter(Task.platform_task_id == platform_task_id, RequestLog.user_id == user_id)
        .order_by(Task.id.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    request_log = (
        db.query(RequestLog)
        .filter(RequestLog.id == row.request_id)
        .first()
    )
    if request_log is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    return row, request_log.route_group


def _build_query_invoke_ctx(provider, task: Task, *, route_group: str) -> dict[str, object]:
    if route_group == "minimax_t2a_async":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "minimax_t2a_async",
            "path": f"/v1/query/t2a_async_query_v2?task_id={task.provider_task_id}",
            "method": "GET",
        }
    if route_group == "minimax_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "minimax_video",
            "path": f"/v1/query/video_generation?task_id={task.provider_task_id}",
            "method": "GET",
        }
    if route_group == "kling_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "kling_video",
            "path": f"/v1/videos/omni-video/{task.provider_task_id}",
            "method": "GET",
        }
    if route_group == "wan_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "wan_video",
            "path": f"/api/v1/tasks/{task.provider_task_id}",
            "method": "GET",
        }
    if route_group == "vidu":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "vidu",
            "path": f"/ent/v2/tasks/{task.provider_task_id}/creations",
            "method": "GET",
        }
    return {
        "provider": provider,
        "provider_model": task,
        "route_group": route_group,
        "method": "GET",
    }


def _build_content_ctx(provider, task: Task, *, route_group: str) -> dict[str, object]:
    if route_group == "minimax_t2a_async":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "minimax_t2a_async",
        }
    if route_group == "minimax_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "minimax_video",
        }
    if route_group == "kling_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "kling_video",
        }
    if route_group == "wan_video":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "wan_video",
        }
    if route_group == "vidu":
        return {
            "provider": provider,
            "provider_model": task,
            "route_group": "vidu",
        }
    return {
        "provider": provider,
        "provider_model": task,
        "route_group": route_group,
    }


def _build_response(task: Task, result: dict[str, object]) -> dict[str, object]:
    response_body = dict(result)
    response_body["id"] = task.platform_task_id
    response_body["provider_task_id"] = task.provider_task_id
    response_body.setdefault("model", task.public_model_code)
    if response_body.get("created_at") is None and task.created_at is not None:
        response_body["created_at"] = int(task.created_at.replace(tzinfo=timezone.utc).timestamp())
    return response_body


@router.get(
    "/v1/tasks/{task_id}",
    summary="查询异步任务",
    response_model=VideoTaskResponse,
    responses={**AUTH_ERROR_RESPONSES, **TASK_NOT_FOUND_RESPONSE},
)
async def get_task(
    task_id: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """查询当前 API Key 所属用户创建的异步视频任务。"""
    task, route_group = _get_task_with_route_group(db, task_id, ctx.user_id)
    service = AsyncTaskExecutionService(db)
    return await service.get_task(
        http_request=http_request,
        ctx=ctx,
        task=task,
        route_group=route_group,
        task_invoke_builder=lambda provider, task: _build_query_invoke_ctx(provider, task, route_group=route_group),
        response_builder=_build_response,
    )


@router.get(
    "/v1/tasks/{task_id}/content",
    summary="下载异步任务内容",
    responses={**AUTH_ERROR_RESPONSES, **TASK_NOT_FOUND_RESPONSE},
)
async def get_task_content(
    task_id: str,
    http_request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """下载当前用户已完成异步视频任务生成的内容。"""
    task, route_group = _get_task_with_route_group(db, task_id, ctx.user_id)
    service = AsyncTaskExecutionService(db)
    return await service.download_content(
        http_request=http_request,
        ctx=ctx,
        task=task,
        route_group=route_group,
        task_content_builder=lambda provider, task: _build_content_ctx(provider, task, route_group=route_group),
    )
