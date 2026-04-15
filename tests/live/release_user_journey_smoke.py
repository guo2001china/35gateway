#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "api"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "output" / "live"
OUTPUT_PATH = OUTPUT_DIR / "release-user-journey-smoke-report.json"
DEFAULT_SMOKE_DB_PATH = BACKEND_ROOT / "data" / "release-user-journey-smoke.sqlite3"


def _bootstrap_isolated_sqlite_db() -> None:
    database_url = str(
        os.getenv("API35_SMOKE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or f"sqlite:///{DEFAULT_SMOKE_DB_PATH}"
    ).strip()
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if not db_path.is_absolute():
            db_path = (BACKEND_ROOT / db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()
    os.environ["DATABASE_URL"] = database_url
    os.environ["API35_DATABASE_URL"] = database_url


_bootstrap_isolated_sqlite_db()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.provider_catalog import get_provider  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domains.platform.entities.entities import ProviderAccount, ProviderRequest, Request, User  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.live.public_model_live_smoke import iso_now  # noqa: E402


PROVIDER_ENV_FALLBACKS: dict[str, dict[str, str]] = {
    "yunwu_openai": {
        "api_key": "API35_YUNWU_OPENAI_API_KEY",
        "base_url": "API35_YUNWU_OPENAI_BASE_URL",
    },
}


@dataclass
class SmokeContext:
    client: TestClient
    session_token: str
    user_id: int
    api_key: str
    yunwu_enabled: bool


def _load_local_env() -> dict[str, str]:
    env_path = BACKEND_ROOT / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def _request_json(
    client: TestClient,
    method: str,
    path: str,
    *,
    ok_statuses: tuple[int, ...] = (200,),
    **kwargs: Any,
) -> dict[str, Any]:
    response = client.request(method, path, **kwargs)
    if response.status_code not in ok_statuses:
        raise AssertionError(
            f"{method} {path} failed: status={response.status_code}\nbody={response.text[:4000]}"
        )
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise AssertionError(f"{method} {path} returned non-json: {content_type}")
    return response.json()


def _request_raw(
    client: TestClient,
    method: str,
    path: str,
    *,
    ok_statuses: tuple[int, ...] = (200,),
    **kwargs: Any,
):
    response = client.request(method, path, **kwargs)
    if response.status_code not in ok_statuses:
        raise AssertionError(
            f"{method} {path} failed: status={response.status_code}\nbody={response.text[:4000]}"
        )
    return response


def _create_temp_user_session(client: TestClient) -> dict[str, Any]:
    email = f"release-smoke-{int(time.time())}@35m.ai"
    send_payload = _request_json(
        client,
        "POST",
        "/auth/email/send-code",
        ok_statuses=(200, 201),
        json={"email": email},
    )
    code = str(send_payload.get("debug_code") or "")
    if not code.isdigit():
        raise AssertionError(f"invalid email verification payload: {send_payload}")
    login_payload = _request_json(
        client,
        "POST",
        "/auth/login/email",
        ok_statuses=(200, 201),
        json={"email": email, "code": code},
    )
    token = str(login_payload.get("session_token") or "")
    if not token.startswith("sess_api35_"):
        raise AssertionError(f"invalid session token payload: {login_payload}")
    user = login_payload.get("user") or {}
    return {
        "session_token": token,
        "user_id": int(user.get("user_id")),
        "email": email,
    }


def _prepare_user_provider_account(
    client: TestClient,
    *,
    session_token: str,
    user_id: int,
    provider_code: str,
) -> bool:
    provider = get_provider(provider_code)
    local_env = _load_local_env()
    env_mapping = PROVIDER_ENV_FALLBACKS.get(provider_code, {})
    credential_payload = {
        str(key): str(value)
        for key, value in (provider.auth_config or {}).items()
        if str(value or "").strip()
    }
    if not credential_payload:
        api_key_env = env_mapping.get("api_key")
        api_key = str(os.getenv(api_key_env or "", "") or local_env.get(api_key_env or "", "")).strip()
        if api_key:
            credential_payload = {"api_key": api_key}
    base_url_override = str(provider.base_url or "").strip()
    if not base_url_override:
        base_url_env = env_mapping.get("base_url")
        base_url_override = str(
            os.getenv(base_url_env or "", "") or local_env.get(base_url_env or "", "")
        ).strip()
    if not credential_payload:
        return False

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise AssertionError(f"user not found: {user_id}")
        user.balance = Decimal("100")
        db.query(ProviderAccount).filter(
            ProviderAccount.user_id == user_id,
            ProviderAccount.provider_code == provider_code,
        ).delete(synchronize_session=False)
        db.commit()

    payload = {
        "provider_code": provider_code,
        "display_name": f"{provider_code} release smoke",
        "base_url_override": base_url_override or None,
        "credential_payload": credential_payload,
        "priority": 10,
    }
    _request_json(
        client,
        "POST",
        "/v1/provider-accounts",
        ok_statuses=(200, 201),
        headers={"Authorization": f"Bearer {session_token}"},
        json=payload,
    )
    return True


def _fetch_system_default_api_key(client: TestClient, *, session_token: str) -> str:
    payload = _request_json(
        client,
        "GET",
        "/v1/api-keys/system-default",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    api_key = str(payload.get("api_key") or "")
    if not api_key.startswith("ak_api35_"):
        raise AssertionError(f"invalid system api key payload: {payload}")
    return api_key


def _before_request_id() -> int:
    with SessionLocal() as db:
        row = db.query(Request.id).order_by(Request.id.desc()).first()
        return int(row[0]) if row else 0


def _poll_new_request(*, user_id: int, after_id: int, timeout_seconds: int = 30) -> Request:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with SessionLocal() as db:
            row = (
                db.query(Request)
                .filter(Request.user_id == user_id, Request.id > after_id)
                .order_by(Request.id.asc())
                .first()
            )
            if row is not None:
                return row
        time.sleep(0.5)
    raise AssertionError(f"timed out waiting for request row after id={after_id}")


def _fetch_provider_attempts(request_pk: int) -> list[ProviderRequest]:
    with SessionLocal() as db:
        return (
            db.query(ProviderRequest)
            .filter(ProviderRequest.request_id == request_pk)
            .order_by(ProviderRequest.id.asc())
            .all()
        )


def _poll_task(client: TestClient, *, api_key: str, task_id: str, timeout_seconds: int = 300) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] | None = None
    while time.time() < deadline:
        last_payload = _request_json(
            client,
            "GET",
            f"/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        status = str(last_payload.get("status") or "").lower()
        if status in {"completed", "failed", "canceled"}:
            return last_payload
        time.sleep(2.0)
    raise AssertionError(f"task polling timed out: {json.dumps(last_payload or {}, ensure_ascii=False, indent=2)}")


def _extract_text_content(payload: dict[str, Any]) -> str:
    return str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()


def _run_step(name: str, func: Callable[[], dict[str, Any]], report: dict[str, Any]) -> dict[str, Any] | None:
    try:
        result = func()
        report["steps"].append({"name": name, "status": "passed", **result})
        return result
    except Exception as exc:
        report["steps"].append({"name": name, "status": "failed", "error": str(exc)})
        return None


def main() -> int:
    report: dict[str, Any] = {
        "generated_at": iso_now(),
        "database_url": os.environ.get("DATABASE_URL", ""),
        "steps": [],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    app = create_app()
    with TestClient(app) as client:
        smoke_user = _create_temp_user_session(client)
        session_token = str(smoke_user["session_token"])
        user_id = int(smoke_user["user_id"])
        api_key = _fetch_system_default_api_key(client, session_token=session_token)
        yunwu_enabled = _prepare_user_provider_account(
            client,
            session_token=session_token,
            user_id=user_id,
            provider_code="yunwu_openai",
        )
        ctx = SmokeContext(
            client=client,
            session_token=session_token,
            user_id=user_id,
            api_key=api_key,
            yunwu_enabled=yunwu_enabled,
        )

        _run_step(
            "site_pages",
            lambda: {
                "docs_status": _request_raw(client, "GET", "/docs").status_code,
                "models_status": _request_raw(client, "GET", "/models").status_code,
                "console_login_status": _request_raw(client, "GET", "/console/login").status_code,
            },
            report,
        )

        _run_step(
            "catalog",
            lambda: {
                "public_model_count": len(_request_json(client, "GET", "/v1/models")),
            },
            report,
        )

        def _default_text() -> dict[str, Any]:
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                json={
                    "model": "gpt-5.4",
                    "messages": [{"role": "user", "content": "reply exactly: RELEASE-DEFAULT-GPT-5.4"}],
                    "max_tokens": 16,
                },
                ok_statuses=(200, 201),
            )
            content = _extract_text_content(body)
            if "RELEASE-DEFAULT-GPT-5.4" not in content:
                raise AssertionError(f"unexpected content: {content!r}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            attempts = _fetch_provider_attempts(request_row.id)
            return {
                "request_id": request_row.request_id,
                "route_plan": request_row.route_plan,
                "provider_attempts": [
                    {
                        "provider_code": row.provider_code,
                        "status": row.status,
                        "http_status": row.http_status_code,
                        "error": row.error_message,
                    }
                    for row in attempts
                ],
            }

        _run_step("default_text_gpt54", _default_text, report)

        def _mixed_text_primary() -> dict[str, Any]:
            if not ctx.yunwu_enabled:
                raise AssertionError("yunwu_openai not configured")
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {ctx.api_key}",
                    "X-API35-Chain": "yunwu_openai,35m",
                },
                json={
                    "model": "gpt-5.4",
                    "messages": [{"role": "user", "content": "reply exactly: RELEASE-MIXED-GPT-5.4"}],
                    "max_tokens": 16,
                },
                ok_statuses=(200, 201),
            )
            content = _extract_text_content(body)
            if "RELEASE-MIXED-GPT-5.4" not in content:
                raise AssertionError(f"unexpected mixed content: {content!r}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            attempts = _fetch_provider_attempts(request_row.id)
            return {
                "request_id": request_row.request_id,
                "route_plan": request_row.route_plan,
                "provider_attempts": [
                    {
                        "provider_code": row.provider_code,
                        "status": row.status,
                        "http_status": row.http_status_code,
                        "error": row.error_message,
                    }
                    for row in attempts
                ],
            }

        _run_step("mixed_text_gpt54", _mixed_text_primary, report)

        def _mixed_text_fallback() -> dict[str, Any]:
            if not ctx.yunwu_enabled:
                raise AssertionError("yunwu_openai not configured")
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {ctx.api_key}",
                    "X-API35-Chain": "yunwu_openai,35m",
                },
                json={
                    "model": "DeepSeek-V3.2",
                    "messages": [{"role": "user", "content": "reply exactly: RELEASE-MIXED-DEEPSEEK"}],
                    "max_tokens": 16,
                },
                ok_statuses=(200, 201),
            )
            content = _extract_text_content(body)
            if "RELEASE-MIXED-DEEPSEEK" not in content:
                raise AssertionError(f"unexpected mixed fallback content: {content!r}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            attempts = _fetch_provider_attempts(request_row.id)
            return {
                "request_id": request_row.request_id,
                "route_plan": request_row.route_plan,
                "provider_attempts": [
                    {
                        "provider_code": row.provider_code,
                        "status": row.status,
                        "http_status": row.http_status_code,
                        "error": row.error_message,
                    }
                    for row in attempts
                ],
            }

        _run_step("mixed_text_deepseek_fallback", _mixed_text_fallback, report)

        def _image_seedream() -> dict[str, Any]:
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/doubao-seedream-5.0-lite",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                json={
                    "prompt": "极简蓝白科技工作台海报",
                    "response_format": "url",
                    "watermark": False,
                    "output_format": "png",
                },
                ok_statuses=(200, 201),
            )
            output = body.get("output") or {}
            images = body.get("images") or []
            first_image = images[0] if isinstance(images, list) and images else {}
            image_url = str(
                output.get("image_url")
                or output.get("url")
                or (first_image.get("url") if isinstance(first_image, dict) else "")
                or ""
            )
            if not image_url:
                raise AssertionError(f"image response missing url: {body}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            return {"request_id": request_row.request_id, "image_url": image_url}

        _run_step("image_seedream5_lite", _image_seedream, report)

        def _audio_qwen_tts() -> dict[str, Any]:
            voices = _request_json(
                client,
                "GET",
                "/v1/qwen/system-voices",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
            ).get("items") or []
            voice = str((voices[0] or {}).get("voice") or "") if voices else ""
            if not voice:
                raise AssertionError("no qwen system voice available")
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/qwen/system-tts",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                json={
                    "text": "欢迎来到 35m，这是一条发布前真实用户旅程烟测语音。",
                    "voice": voice,
                    "language_type": "Chinese",
                },
                ok_statuses=(200, 201),
            )
            audio_url = str((((body.get("output") or {}).get("audio") or {}).get("url")) or "")
            if not audio_url:
                raise AssertionError(f"qwen system tts missing audio url: {body}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            return {"request_id": request_row.request_id, "voice": voice, "audio_url": audio_url}

        _run_step("audio_qwen_system_tts", _audio_qwen_tts, report)

        def _audio_minimax_tts() -> dict[str, Any]:
            voices = _request_json(
                client,
                "GET",
                "/v1/minimax/system-voices",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
            ).get("items") or []
            voice_id = str((voices[0] or {}).get("voice_id") or "") if voices else ""
            if not voice_id:
                raise AssertionError("no minimax system voice available")
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/minimax/system-tts",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                json={
                    "model": "speech-2.8-turbo",
                    "text": "Welcome to 35m, this is a release smoke audio sample.",
                    "voice_id": voice_id,
                    "audio_setting": {"format": "mp3"},
                },
                ok_statuses=(200, 201),
            )
            task_id = str(body.get("id") or "")
            if not task_id.startswith("task_"):
                raise AssertionError(f"unexpected minimax tts task response: {body}")
            task_detail = _poll_task(client, api_key=ctx.api_key, task_id=task_id, timeout_seconds=180)
            if str(task_detail.get("status") or "").lower() != "completed":
                raise AssertionError(f"minimax tts task not completed: {task_detail}")
            content_response = _request_raw(
                client,
                "GET",
                f"/v1/tasks/{task_id}/content",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                ok_statuses=(200,),
            )
            return {
                "task_id": task_id,
                "task_status": task_detail.get("status"),
                "content_type": content_response.headers.get("content-type"),
            }

        _run_step("audio_minimax_system_tts", _audio_minimax_tts, report)

        def _video_seedance() -> dict[str, Any]:
            before_id = _before_request_id()
            body = _request_json(
                client,
                "POST",
                "/v1/seedance-2.0-fast",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                json={
                    "prompt": "A clean product launch cinematic clip.",
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                    "seconds": 4,
                    "generate_audio": False,
                },
                ok_statuses=(200, 201),
            )
            task_id = str(body.get("id") or "")
            if not task_id.startswith("task_"):
                raise AssertionError(f"unexpected seedance task response: {body}")
            request_row = _poll_new_request(user_id=ctx.user_id, after_id=before_id)
            task_detail = _poll_task(client, api_key=ctx.api_key, task_id=task_id, timeout_seconds=300)
            if str(task_detail.get("status") or "").lower() != "completed":
                raise AssertionError(f"seedance task not completed: {task_detail}")
            content_response = _request_raw(
                client,
                "GET",
                f"/v1/tasks/{task_id}/content",
                headers={"Authorization": f"Bearer {ctx.api_key}"},
                ok_statuses=(200,),
            )
            return {
                "request_id": request_row.request_id,
                "task_id": task_id,
                "task_status": task_detail.get("status"),
                "content_type": content_response.headers.get("content-type"),
            }

        _run_step("video_seedance20_fast", _video_seedance, report)

        _run_step(
            "logout",
            lambda: {
                "logout_status": _request_raw(
                    client,
                    "POST",
                    "/auth/session/logout",
                    headers={"Authorization": f"Bearer {ctx.session_token}"},
                    ok_statuses=(200,),
                ).status_code,
                "post_logout_status": _request_raw(
                    client,
                    "GET",
                    "/auth/session/me",
                    headers={"Authorization": f"Bearer {ctx.session_token}"},
                    ok_statuses=(401,),
                ).status_code,
            },
            report,
        )

    report["summary"] = {
        "passed": sum(1 for item in report["steps"] if item["status"] == "passed"),
        "failed": sum(1 for item in report["steps"] if item["status"] == "failed"),
    }
    report["status"] = "failed" if report["summary"]["failed"] else "passed"
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
