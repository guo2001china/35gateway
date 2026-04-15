from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.routes.models.tasks import _build_query_invoke_ctx, _build_response, _get_task_with_route_group


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def join(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result


class _FakeDB:
    def __init__(self, *, task_row, request_row):
        self.task_row = task_row
        self.request_row = request_row

    def query(self, model):
        if model.__name__ == "Task":
            return _FakeQuery(self.task_row)
        return _FakeQuery(self.request_row)


def test_build_query_context_for_minimax_video_task() -> None:
    provider = SimpleNamespace(provider_code="minimax_official")
    task = SimpleNamespace(public_model_code="minimax-hailuo-02", provider_task_id="380089806868558")

    ctx = _build_query_invoke_ctx(provider, task, route_group="minimax_video")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "minimax_video",
        "path": "/v1/query/video_generation?task_id=380089806868558",
        "method": "GET",
    }


def test_build_query_context_for_minimax_t2a_async_task() -> None:
    provider = SimpleNamespace(provider_code="minimax_official")
    task = SimpleNamespace(public_model_code="speech-2.8-hd", provider_task_id="minimax-task-123")

    ctx = _build_query_invoke_ctx(provider, task, route_group="minimax_t2a_async")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "minimax_t2a_async",
        "path": "/v1/query/t2a_async_query_v2?task_id=minimax-task-123",
        "method": "GET",
    }


def test_build_query_context_for_wan_video_task() -> None:
    provider = SimpleNamespace(provider_code="wan_official")
    task = SimpleNamespace(public_model_code="wan2.6", provider_task_id="dashscope-task-123")

    ctx = _build_query_invoke_ctx(provider, task, route_group="wan_video")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "wan_video",
        "path": "/api/v1/tasks/dashscope-task-123",
        "method": "GET",
    }


def test_build_query_context_for_kling_video_task() -> None:
    provider = SimpleNamespace(provider_code="kling_official")
    task = SimpleNamespace(public_model_code="kling-o1", provider_task_id="kling-task-123")

    ctx = _build_query_invoke_ctx(provider, task, route_group="kling_video")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "kling_video",
        "path": "/v1/videos/omni-video/kling-task-123",
        "method": "GET",
    }


def test_build_query_context_for_vidu_task() -> None:
    provider = SimpleNamespace(provider_code="vidu_official")
    task = SimpleNamespace(public_model_code="viduq3-pro", provider_task_id="vidu-task-123")

    ctx = _build_query_invoke_ctx(provider, task, route_group="vidu")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "vidu",
        "path": "/ent/v2/tasks/vidu-task-123/creations",
        "method": "GET",
    }


def test_build_content_context_for_minimax_t2a_async_task() -> None:
    provider = SimpleNamespace(provider_code="minimax_official")
    task = SimpleNamespace(public_model_code="speech-2.8-hd", provider_task_id="minimax-task-123")

    from app.api.routes.models.tasks import _build_content_ctx

    ctx = _build_content_ctx(provider, task, route_group="minimax_t2a_async")

    assert ctx == {
        "provider": provider,
        "provider_model": task,
        "route_group": "minimax_t2a_async",
    }


def test_build_response_backfills_created_at_for_minimax_video_task() -> None:
    task = SimpleNamespace(
        public_model_code="minimax-hailuo-2.3",
        platform_task_id="task_demo",
        provider_task_id="provider_demo",
        created_at=datetime(2026, 3, 24, 8, 0, tzinfo=timezone.utc),
    )

    response = _build_response(task, {"status": "submitted"})

    assert response == {
        "id": "task_demo",
        "provider_task_id": "provider_demo",
        "model": "minimax-hailuo-2.3",
        "created_at": 1774339200,
        "status": "submitted",
    }


def test_get_task_with_route_group_reads_request_route_group_instead_of_model_prefix() -> None:
    task = SimpleNamespace(
        platform_task_id="task_demo",
        request_id=12,
        public_model_code="wan2.6",
    )
    request_log = SimpleNamespace(id=12, route_group="kling_video")

    resolved_task, route_group = _get_task_with_route_group(
        _FakeDB(task_row=task, request_row=request_log),
        "task_demo",
        user_id=9,
    )

    assert resolved_task is task
    assert route_group == "kling_video"


def test_get_task_with_route_group_raises_when_request_log_is_missing() -> None:
    task = SimpleNamespace(platform_task_id="task_demo", request_id=12, public_model_code="wan2.6")

    with pytest.raises(Exception) as exc_info:
        _get_task_with_route_group(
            _FakeDB(task_row=task, request_row=None),
            "task_demo",
            user_id=9,
        )

    assert getattr(exc_info.value, "status_code", None) == 404
    assert getattr(exc_info.value, "detail", None) == "task_not_found"
