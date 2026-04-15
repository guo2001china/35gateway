#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.provider_catalog import get_provider  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domains.platform.entities.entities import Task, User  # noqa: E402
from app.domains.platform.providers.registry import get_adapter  # noqa: E402


OUTPUT_DIR = REPO_ROOT / "artifacts" / "output" / "playwright"
OUTPUT_PATH = OUTPUT_DIR / "public-model-live-smoke-report.json"
LAST_REPORT: dict[str, Any] | None = None
IMAGE_URL = "https://dummyimage.com/1024x576/ffffff/111111.png&text=35gateway-smoke"
IMAGE_URL_ALT = "https://dummyimage.com/768x768/eef4ff/111111.png&text=35gateway-alt"
ACTIVE_TASK_STATUSES = {"submitted", "queued", "processing"}
ASYNC_VIDEO_MODELS = {
    "veo-3",
    "veo-3-fast",
    "veo-3.1",
    "veo-3.1-fast",
    "wan2.6",
    "wan2.6-flash",
    "minimax-hailuo-02",
    "minimax-hailuo-2.3",
    "minimax-hailuo-2.3-fast",
    "kling-o1",
}
CAPACITY_RETRY_TIMEOUT_SECONDS = 5


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def archived_output_path(generated_at: str) -> Path:
    dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    stamp = dt.strftime("%Y%m%dT%H%M%SZ")
    return OUTPUT_DIR / f"public-model-live-smoke-report-{stamp}.json"


def write_report(report: dict[str, Any]) -> None:
    report["total"] = len(report.get("results") or [])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    OUTPUT_PATH.write_text(serialized, encoding="utf-8")
    archived_output_path(str(report.get("generated_at") or iso_now())).write_text(serialized, encoding="utf-8")


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    ok_statuses: tuple[int, ...] = (200,),
    timeout: int = 240,
    **kwargs: Any,
) -> requests.Response:
    response = session.request(method, url, timeout=timeout, **kwargs)
    if response.status_code not in ok_statuses:
        raise AssertionError(
            f"{method} {url} failed: status={response.status_code}\nbody={response.text[:4000]}"
        )
    return response


def _request_with_capacity_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    retry_error_substrings: tuple[str, ...],
    retry_label: str = "",
    retry_timeout_seconds: int = 300,
    retry_interval_seconds: float = 10.0,
    ok_statuses: tuple[int, ...] = (200,),
    timeout: int = 240,
    **kwargs: Any,
) -> requests.Response:
    deadline = time.time() + retry_timeout_seconds
    last_error = ""
    retry_count = 0
    while True:
        response = session.request(method, url, timeout=timeout, **kwargs)
        if response.status_code in ok_statuses:
            return response
        body = response.text[:4000]
        if response.status_code == 502 and any(token in body for token in retry_error_substrings) and time.time() < deadline:
            last_error = body
            retry_count += 1
            if retry_count == 1 or retry_count % 6 == 0:
                label = retry_label or url
                remaining = max(0, int(deadline - time.time()))
                print(
                    f"[smoke] retrying {label} after capacity limit "
                    f"(attempt={retry_count}, remaining={remaining}s)",
                    flush=True,
                )
            time.sleep(retry_interval_seconds)
            continue
        raise AssertionError(f"{method} {url} failed: status={response.status_code}\nbody={body}")
    raise AssertionError(
        f"capacity_limited after retry window.\nLast error:\n{last_error}"
    )


def _poll(fetcher, *, timeout_seconds: int, interval_seconds: float, predicate, description: str):
    deadline = time.time() + timeout_seconds
    last_payload: Any = None
    while time.time() < deadline:
        last_payload = fetcher()
        if predicate(last_payload):
            return last_payload
        time.sleep(interval_seconds)
    raise AssertionError(
        f"Timed out waiting for {description}.\nLast payload:\n{json.dumps(last_payload, ensure_ascii=False, indent=2, default=str)}"
    )


def _user_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def _api_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def create_temp_user_session(session: requests.Session, backend_url: str) -> dict[str, Any]:
    email = f"public-smoke-{int(time.time())}@35m.ai"
    send_payload = _request(
        session,
        "POST",
        f"{backend_url}/auth/email/send-code",
        ok_statuses=(200, 201),
        json={"email": email},
    ).json()
    code = str(send_payload.get("debug_code") or "")
    if not code.isdigit():
        raise AssertionError(f"invalid debug email code payload: {send_payload}")
    payload = _request(
        session,
        "POST",
        f"{backend_url}/auth/login/email",
        ok_statuses=(200, 201),
        json={"email": email, "code": code},
    ).json()
    token = str(payload.get("session_token") or "")
    if not token.startswith("sess_api35_"):
        raise AssertionError(f"invalid session token payload: {payload}")
    return {
        "email": email,
        "session_token": token,
        "user": payload.get("user") or {},
    }


def ensure_smoke_balance(user_id: int, *, minimum_balance: Decimal = Decimal("500000")) -> dict[str, str]:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise AssertionError(f"smoke user not found: user_id={user_id}")
        current_balance = Decimal(str(user.balance or "0"))
        if current_balance < minimum_balance:
            user.balance = minimum_balance
            db.add(user)
            db.commit()
            db.refresh(user)
        return {
            "user_id": str(user.id),
            "balance": str(user.balance),
        }


def fetch_system_default_api_key(session: requests.Session, backend_url: str, session_token: str) -> str:
    payload = _request(
        session,
        "GET",
        f"{backend_url}/v1/api-keys/system-default",
        headers=_user_headers(session_token),
    ).json()
    api_key = str(payload.get("api_key") or "")
    if not api_key.startswith("ak_api35_"):
        raise AssertionError(f"invalid system api key payload: {payload}")
    return api_key


def fetch_user_logs(session: requests.Session, backend_url: str, session_token: str) -> dict[str, Any]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/logs",
        headers=_user_headers(session_token),
        params={"page": 1, "size": 100},
    ).json()


def fetch_log_detail(session: requests.Session, backend_url: str, session_token: str, request_id: str) -> dict[str, Any]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/logs/{request_id}",
        headers=_user_headers(session_token),
    ).json()


def poll_new_log(session: requests.Session, backend_url: str, session_token: str, before_ids: set[str]) -> dict[str, Any]:
    return _poll(
        lambda: [
            item
            for item in fetch_user_logs(session, backend_url, session_token)["items"]
            if str(item.get("request_id") or "") not in before_ids
        ],
        timeout_seconds=240,
        interval_seconds=2,
        predicate=lambda items: bool(items),
        description="new public model request log",
    )[0]


def fetch_task_detail(session: requests.Session, backend_url: str, api_key: str, task_id: str) -> dict[str, Any]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/tasks/{task_id}",
        headers=_api_headers(api_key),
    ).json()


def fetch_task_content(session: requests.Session, backend_url: str, api_key: str, task_id: str) -> requests.Response:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/tasks/{task_id}/content",
        headers=_api_headers(api_key),
        ok_statuses=(200,),
        timeout=300,
    )


def wait_for_task_terminal(
    session: requests.Session,
    backend_url: str,
    api_key: str,
    task_id: str,
    *,
    initial_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_payload = initial_payload
    if initial_payload and str(initial_payload.get("status") or "").lower() not in ACTIVE_TASK_STATUSES:
        return initial_payload

    deadline = time.time() + 300
    if initial_payload is not None:
        time.sleep(5.0)
    while time.time() < deadline:
        try:
            last_payload = fetch_task_detail(session, backend_url, api_key, task_id)
        except requests.RequestException:
            time.sleep(3.5)
            continue
        except AssertionError:
            raise
        if str((last_payload or {}).get("status") or "").lower() not in ACTIVE_TASK_STATUSES:
            return last_payload
        time.sleep(5.0)
    raise AssertionError(
        f"Timed out waiting for task {task_id} to reach terminal state.\nLast payload:\n{json.dumps(last_payload, ensure_ascii=False, indent=2, default=str)}"
    )


async def reconcile_stale_async_video_tasks() -> int:
    db = SessionLocal()
    try:
        updated = 0
        provider_queries = (
            (
                "minimax_official",
                lambda row: str(row.model_code or "").startswith("minimax-hailuo"),
                lambda row: {
                    "provider": get_provider("minimax_official"),
                    "provider_model": row,
                    "route_group": "minimax_video",
                    "path": f"/v1/query/video_generation?task_id={row.provider_task_id}",
                    "method": "GET",
                },
            ),
            (
                "wan_official",
                lambda row: str(row.model_code or "").startswith("wan2.6"),
                lambda row: {
                    "provider": get_provider("wan_official"),
                    "provider_model": row,
                    "route_group": "wan_video",
                    "path": f"/api/v1/tasks/{row.provider_task_id}",
                    "method": "GET",
                },
            ),
        )

        for provider_code, row_filter, invoke_builder in provider_queries:
            rows = (
                db.query(Task)
                .filter(Task.provider_code == provider_code)
                .filter(Task.status.in_(tuple(ACTIVE_TASK_STATUSES)))
                .all()
            )
            if not rows:
                continue
            provider = get_provider(provider_code)
            adapter = get_adapter(provider.adapter_key)
            for row in rows:
                if not row_filter(row):
                    continue
                try:
                    result = await adapter.invoke(invoke_builder(row))
                except Exception:
                    continue

                status = str((result or {}).get("status") or row.status).lower()
                if status in ACTIVE_TASK_STATUSES:
                    continue
                row.status = status
                row.result_payload = result
                row.finished_at = datetime.now(timezone.utc)
                db.add(row)
                updated += 1
        if updated:
            db.commit()
        return updated
    finally:
        db.close()


def fetch_public_models(session: requests.Session, backend_url: str) -> list[dict[str, Any]]:
    return _request(session, "GET", f"{backend_url}/v1/models").json()


def fetch_model_detail(session: requests.Session, backend_url: str, model_code: str) -> dict[str, Any]:
    return _request(session, "GET", f"{backend_url}/v1/models/{model_code}").json()


def list_qwen_system_voices(session: requests.Session, backend_url: str, api_key: str) -> list[dict[str, Any]]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/qwen/system-voices",
        headers=_api_headers(api_key),
    ).json()["items"]


def list_qwen_cloned_voices(session: requests.Session, backend_url: str, api_key: str) -> list[dict[str, Any]]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/qwen/voice-clones?page_index=0&page_size=100",
        headers=_api_headers(api_key),
    ).json()["items"]


def list_minimax_system_voices(session: requests.Session, backend_url: str, api_key: str) -> list[dict[str, Any]]:
    return _request(
        session,
        "GET",
        f"{backend_url}/v1/minimax/system-voices",
        headers=_api_headers(api_key),
    ).json()["items"]


def create_qwen_clone_voice(session: requests.Session, backend_url: str, api_key: str, audio_url: str) -> dict[str, Any]:
    return _request(
        session,
        "POST",
        f"{backend_url}/v1/qwen/voice-clones",
        headers=_api_headers(api_key),
        ok_statuses=(200, 201),
        json={
            "name": f"smoke_{int(time.time())}",
            "audio_url": audio_url,
            "text": "欢迎来到 35m，这是一段用于公开模型烟测的参考音频。",
            "language": "zh",
        },
    ).json()


def wait_for_qwen_cloned_voice(
    session: requests.Session,
    backend_url: str,
    api_key: str,
    voice: str,
) -> str:
    result = _poll(
        lambda: list_qwen_cloned_voices(session, backend_url, api_key),
        timeout_seconds=120,
        interval_seconds=2.0,
        predicate=lambda items: any(str(item.get("voice") or "") == voice for item in items),
        description=f"qwen cloned voice {voice}",
    )
    matched = next((str(item.get("voice") or "") for item in result if str(item.get("voice") or "") == voice), "")
    if not matched:
        raise AssertionError(f"qwen cloned voice {voice} not visible after creation")
    return matched


def build_payload(
    model_code: str,
    detail: dict[str, Any],
    *,
    qwen_standard_voice: str | None,
    qwen_instruct_voice: str | None,
    qwen_cloned_voice: str | None,
    qwen_clone_audio_url: str | None,
    minimax_system_voice: str | None,
) -> tuple[str, dict[str, Any]]:
    endpoint = str(detail.get("endpoints", {}).get("create") or "")
    route_group = str(detail.get("route_group") or "")
    if endpoint == "POST /v1/chat/completions":
        return (
            endpoint,
            {
                "model": model_code,
                "messages": [{"role": "user", "content": f"请只回复 PUBLIC-SMOKE-OK {model_code}"}],
            },
        )
    if endpoint == "POST /v1/responses":
        return (
            endpoint,
            {
                "model": model_code,
                "input": f"请只回复 PUBLIC-SMOKE-OK {model_code}",
            },
        )
    if endpoint.endswith(":generateContent"):
        resolved = endpoint.replace("{model}", model_code)
        return (
            resolved,
            {
                "model": model_code,
                "contents": [{"role": "user", "parts": [{"text": f"请只回复 PUBLIC-SMOKE-OK {model_code}"}]}],
                "generationConfig": {"maxOutputTokens": 32},
            },
        )
    if model_code == "doubao-seedream-4.5":
        return (endpoint, {"prompt": "极简蓝白科技工作台海报", "response_format": "url", "watermark": False})
    if model_code == "doubao-seedream-5.0-lite":
        return (
            endpoint,
            {
                "prompt": "极简蓝白科技工作台海报",
                "response_format": "url",
                "watermark": False,
                "output_format": "png",
            },
        )
    if model_code in {"seedance-2.0", "seedance-2.0-fast"}:
        return (
            endpoint,
            {
                "prompt": "A clean product launch cinematic clip.",
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "seconds": 4,
                "generate_audio": False,
            },
        )
    if model_code == "nano-banana":
        return (endpoint, {"prompt": "极简蓝白科技工作台海报", "aspect_ratio": "1:1", "resolution": "1K"})
    if model_code == "nano-banana-pro":
        return (endpoint, {"prompt": "极简蓝白科技工作台海报", "aspect_ratio": "1:1", "resolution": "1K"})
    if model_code == "nano-banana-2":
        return (endpoint, {"prompt": "极简蓝白科技工作台海报", "aspect_ratio": "1:1", "resolution": "512"})
    if model_code == "qwen-voice-enrollment":
        if not qwen_clone_audio_url:
            raise AssertionError("qwen clone audio url not prepared")
        return (
            endpoint,
            {
                "name": f"smoke_{int(time.time())}",
                "audio_url": qwen_clone_audio_url,
                "text": "欢迎来到 35m，这是一段用于公开模型烟测的参考音频。",
                "language": "zh",
            },
        )
    if model_code == "qwen3-tts-flash":
        if not qwen_standard_voice:
            raise AssertionError("missing qwen standard voice")
        return (
            endpoint,
            {
                "text": "欢迎来到 35m，这是一条公开模型烟测语音。",
                "voice": qwen_standard_voice,
                "language_type": "Chinese",
            },
        )
    if model_code == "qwen3-tts-instruct-flash":
        if not qwen_instruct_voice:
            raise AssertionError("missing qwen instruct voice")
        return (
            endpoint,
            {
                "text": "欢迎来到 35m，这是一条公开模型烟测语音。",
                "voice": qwen_instruct_voice,
                "mode": "instruct",
                "language_type": "Chinese",
                "instructions": "请用平稳、自然、清晰的品牌旁白口吻朗读。",
            },
        )
    if model_code == "qwen3-tts-vc-2026-01-22":
        if not qwen_cloned_voice:
            raise AssertionError("missing qwen cloned voice")
        return (
            endpoint,
            {
                "text": "欢迎来到 35m，这是一条克隆音色烟测语音。",
                "voice": qwen_cloned_voice,
                "language_type": "Chinese",
            },
        )
    if model_code in {"speech-2.8-hd", "speech-2.8-turbo"}:
        if not minimax_system_voice:
            raise AssertionError("missing minimax system voice")
        return (
            endpoint,
            {
                "text": "Welcome to 35m, this is a public model smoke test audio.",
                "voice_id": minimax_system_voice,
                "audio_setting": {"format": "mp3"},
            },
        )
    if model_code in {"veo-3", "veo-3-fast", "veo-3.1", "veo-3.1-fast"}:
        return (endpoint, {"prompt": "A clean product launch cinematic clip.", "resolution": "720p", "aspect_ratio": "16:9", "seconds": 4})
    if model_code == "wan2.6":
        return (endpoint, {"prompt": "A clean product launch cinematic clip.", "resolution": "720P", "aspect_ratio": "16:9", "seconds": 5})
    if model_code == "wan2.6-flash":
        return (endpoint, {"input_reference": IMAGE_URL, "resolution": "720P", "aspect_ratio": "16:9", "seconds": 5, "generate_audio": False})
    if model_code in {"viduq3-pro", "viduq3-turbo"}:
        return (
            endpoint,
            {
                "mode": "text",
                "prompt": "A clean product launch cinematic clip.",
                "duration": 5,
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "audio": True,
                "off_peak": False,
            },
        )
    if model_code == "minimax-hailuo-02":
        return (endpoint, {"prompt": "A clean product launch cinematic clip.", "resolution": "768P", "aspect_ratio": "16:9", "seconds": 6})
    if model_code == "minimax-hailuo-2.3":
        return (endpoint, {"prompt": "A clean product launch cinematic clip.", "resolution": "768P", "aspect_ratio": "16:9", "seconds": 6})
    if model_code == "minimax-hailuo-2.3-fast":
        return (endpoint, {"input_reference": IMAGE_URL, "resolution": "768P", "aspect_ratio": "16:9", "seconds": 6})
    if model_code == "kling-o1":
        return (endpoint, {"prompt": "A clean product launch cinematic clip.", "mode": "pro", "aspect_ratio": "16:9", "seconds": 5})
    raise AssertionError(f"unsupported public model smoke payload for {model_code!r} / {route_group!r}")


def main() -> int:
    global LAST_REPORT
    parser = argparse.ArgumentParser(description="Run live smoke against all public models.")
    parser.add_argument("--start-after", default="", help="Skip models until after the given model_code.")
    parser.add_argument("--base", default="", help="Override backend base URL, e.g. http://127.0.0.1:8025")
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated model codes to test. When provided, only these public models are exercised.",
    )
    args = parser.parse_args()

    backend_url = (args.base or settings.web_backend_url or "http://127.0.0.1:8025").rstrip("/")
    reconciled_async_tasks = asyncio.run(reconcile_stale_async_video_tasks())
    report: dict[str, Any] = {
        "generated_at": iso_now(),
        "backend_url": backend_url,
        "reconciled_async_tasks": reconciled_async_tasks,
        "status": "running",
        "results": [],
    }
    LAST_REPORT = report
    if reconciled_async_tasks:
        print(f"[smoke] reconciled {reconciled_async_tasks} stale async video tasks", flush=True)

    session = requests.Session()
    session.headers.update({"Accept-Language": "zh-CN"})
    smoke_user = create_temp_user_session(session, backend_url)
    session_token = str(smoke_user["session_token"])
    balance_seed = ensure_smoke_balance(int(smoke_user["user"]["user_id"]))
    system_api_key = fetch_system_default_api_key(session, backend_url, session_token)
    report["balance_seed"] = balance_seed

    public_models = fetch_public_models(session, backend_url)
    only_models = {item.strip() for item in str(args.only or "").split(",") if item.strip()}
    target_models = [str(item["model_code"]) for item in public_models if str(item.get("status") or "").lower() == "available"]
    if only_models:
        target_models = [code for code in target_models if code in only_models]

    qwen_dependency_models = {
        "qwen-voice-enrollment",
        "qwen3-tts-flash",
        "qwen3-tts-instruct-flash",
        "qwen3-tts-vc-2026-01-22",
    }
    needs_qwen_setup = not only_models or any(code in qwen_dependency_models for code in target_models)
    needs_minimax_voices = not only_models or any(code in {"speech-2.8-hd", "speech-2.8-turbo"} for code in target_models)

    qwen_standard_voice: str | None = None
    qwen_instruct_voice: str | None = None
    if needs_qwen_setup:
        qwen_system_voices = list_qwen_system_voices(session, backend_url, system_api_key)
        qwen_standard_voice = next((item["voice"] for item in qwen_system_voices if "standard" in set(item.get("modes") or [])), None)
        qwen_instruct_voice = next((item["voice"] for item in qwen_system_voices if "instruct" in set(item.get("modes") or [])), None)
        if not qwen_standard_voice:
            raise AssertionError("no qwen standard voice available for smoke")
        if not qwen_instruct_voice:
            raise AssertionError("no qwen instruct voice available for smoke")

    minimax_system_voice: str | None = None
    if needs_minimax_voices:
        minimax_system_voices = list_minimax_system_voices(session, backend_url, system_api_key)
        minimax_system_voice = next((item.get("voice_id") for item in minimax_system_voices if item.get("voice_id")), None)
        if not minimax_system_voice:
            raise AssertionError("no minimax system voice available for smoke")

    qwen_clone_audio_url: str | None = None
    qwen_cloned_voice: str | None = None
    pretested_models: set[str] = set()

    if needs_qwen_setup:
        qwen_flash_detail = fetch_model_detail(session, backend_url, "qwen3-tts-flash")
        print("[smoke] pretest qwen3-tts-flash", flush=True)
        qwen_flash_endpoint, qwen_flash_payload = build_payload(
            "qwen3-tts-flash",
            qwen_flash_detail,
            qwen_standard_voice=qwen_standard_voice,
            qwen_instruct_voice=qwen_instruct_voice,
            qwen_cloned_voice=qwen_cloned_voice,
            qwen_clone_audio_url=qwen_clone_audio_url,
            minimax_system_voice=str(minimax_system_voice),
        )
        before_ids = {str(row.get("request_id") or "") for row in fetch_user_logs(session, backend_url, session_token)["items"]}
        qwen_flash_response = _request(
            session,
            "POST",
            f"{backend_url}{qwen_flash_endpoint.replace('POST ', '')}",
            headers=_api_headers(system_api_key),
            ok_statuses=(200, 201),
            json=qwen_flash_payload,
        )
        qwen_flash_log = poll_new_log(session, backend_url, session_token, before_ids)
        qwen_flash_body = qwen_flash_response.json()
        qwen_clone_audio_url = (((qwen_flash_body.get("output") or {}).get("audio") or {}).get("url"))
        if not qwen_clone_audio_url:
            raise AssertionError(f"qwen system tts response missing audio url: {qwen_flash_body}")
        report["results"].append(
            {
                "model_code": "qwen3-tts-flash",
                "status": "passed",
                "endpoint": qwen_flash_endpoint,
                "request_id": qwen_flash_log["request_id"],
                "notes": "used to seed qwen voice clone smoke",
            }
        )
        print(f"[smoke] passed qwen3-tts-flash -> {qwen_flash_log['request_id']}", flush=True)
        pretested_models.add("qwen3-tts-flash")
    start_after = (args.start_after or "").strip()
    passed_start_after = not start_after
    failed_models = 0

    for item in public_models:
        model_code = str(item["model_code"])
        if str(item.get("status") or "").lower() != "available":
            continue
        if model_code in pretested_models:
            continue
        if only_models and model_code not in only_models:
            continue
        if not passed_start_after:
            if model_code == start_after:
                passed_start_after = True
            continue
        endpoint = ""
        try:
            detail = fetch_model_detail(session, backend_url, model_code)

            if model_code == "qwen-voice-enrollment":
                print(f"[smoke] testing {model_code}", flush=True)
                if not qwen_clone_audio_url:
                    raise AssertionError("qwen clone audio url unavailable before voice enrollment smoke")
                before_ids = {
                    str(row.get("request_id") or "")
                    for row in fetch_user_logs(session, backend_url, session_token)["items"]
                }
                clone_payload = create_qwen_clone_voice(session, backend_url, system_api_key, qwen_clone_audio_url)
                qwen_cloned_voice = wait_for_qwen_cloned_voice(
                    session,
                    backend_url,
                    system_api_key,
                    str(clone_payload.get("voice") or ""),
                )
                if not qwen_cloned_voice:
                    raise AssertionError(f"qwen clone voice missing from payload: {clone_payload}")
                new_log = poll_new_log(session, backend_url, session_token, before_ids)
                report["results"].append(
                    {
                        "model_code": model_code,
                        "status": "passed",
                        "endpoint": "/v1/qwen/voice-clones",
                        "request_id": new_log["request_id"],
                        "notes": f"created voice {qwen_cloned_voice}",
                    }
                )
                print(f"[smoke] passed {model_code} -> {new_log['request_id']}", flush=True)
                continue

            endpoint, payload = build_payload(
                model_code,
                detail,
                qwen_standard_voice=qwen_standard_voice,
                qwen_instruct_voice=qwen_instruct_voice,
                qwen_cloned_voice=qwen_cloned_voice,
                qwen_clone_audio_url=qwen_clone_audio_url,
                minimax_system_voice=str(minimax_system_voice),
            )
            if model_code == "qwen3-tts-vc-2026-01-22" and not qwen_cloned_voice:
                if not qwen_clone_audio_url:
                    raise AssertionError("qwen cloned tts smoke missing source audio")
                clone_payload = create_qwen_clone_voice(session, backend_url, system_api_key, qwen_clone_audio_url)
                qwen_cloned_voice = wait_for_qwen_cloned_voice(
                    session,
                    backend_url,
                    system_api_key,
                    str(clone_payload.get("voice") or ""),
                )
                if not qwen_cloned_voice:
                    raise AssertionError(f"qwen clone voice missing from payload: {clone_payload}")
                endpoint, payload = build_payload(
                    model_code,
                    detail,
                    qwen_standard_voice=qwen_standard_voice,
                    qwen_instruct_voice=qwen_instruct_voice,
                    qwen_cloned_voice=qwen_cloned_voice,
                    qwen_clone_audio_url=qwen_clone_audio_url,
                    minimax_system_voice=str(minimax_system_voice),
                )
            print(f"[smoke] testing {model_code}", flush=True)
            before_ids = {str(row.get("request_id") or "") for row in fetch_user_logs(session, backend_url, session_token)["items"]}
            request_kwargs = {
                "headers": _api_headers(system_api_key),
                "ok_statuses": (200, 201),
                "json": payload,
            }
            request_url = f"{backend_url}{endpoint.replace('POST ', '')}"
            if model_code.startswith("minimax-hailuo") or model_code in {"speech-2.8-hd", "speech-2.8-turbo"}:
                response = _request_with_capacity_retry(
                    session,
                    "POST",
                    request_url,
                    retry_error_substrings=(),
                    retry_label=model_code,
                    retry_timeout_seconds=CAPACITY_RETRY_TIMEOUT_SECONDS,
                    **request_kwargs,
                )
            elif model_code.startswith("nano-banana"):
                response = _request_with_capacity_retry(
                    session,
                    "POST",
                    request_url,
                    retry_error_substrings=("ConnectError", "grsai_result_timeout"),
                    retry_label=model_code,
                    **request_kwargs,
                )
            else:
                response = _request(
                    session,
                    "POST",
                    request_url,
                    **request_kwargs,
                )
            new_log = poll_new_log(session, backend_url, session_token, before_ids)
            detail_payload = fetch_log_detail(session, backend_url, session_token, str(new_log["request_id"]))
            row: dict[str, Any] = {
                "model_code": model_code,
                "status": "passed",
                "endpoint": endpoint,
                "request_id": new_log["request_id"],
            }
            body: Any
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text[:500]}

            task_id = body.get("id") if isinstance(body, dict) else None
            if isinstance(task_id, str) and task_id.startswith("task_"):
                task_detail = fetch_task_detail(session, backend_url, system_api_key, task_id)
                row["task_id"] = task_id
                row["task_status"] = task_detail.get("status")
                if model_code in ASYNC_VIDEO_MODELS:
                    final_task_detail = wait_for_task_terminal(
                        session,
                        backend_url,
                        system_api_key,
                        task_id,
                        initial_payload=task_detail,
                    )
                    row["task_status"] = final_task_detail.get("status")
                    if str(final_task_detail.get("status") or "").lower() != "completed":
                        raise AssertionError(
                            f"{model_code} task {task_id} did not complete successfully.\n"
                            f"payload={json.dumps(final_task_detail, ensure_ascii=False, indent=2, default=str)}"
                        )
                    content_response = fetch_task_content(session, backend_url, system_api_key, task_id)
                    row["content_type"] = content_response.headers.get("content-type")
            if model_code == "qwen3-tts-instruct-flash":
                qwen_clone_audio_url = (((body.get("output") or {}).get("audio") or {}).get("url")) or qwen_clone_audio_url
            row["log_status"] = detail_payload.get("status")
            report["results"].append(row)
            print(f"[smoke] passed {model_code} -> {new_log['request_id']}", flush=True)
        except Exception as exc:
            failed_models += 1
            report["results"].append(
                {
                    "model_code": model_code,
                    "status": "failed",
                    "endpoint": endpoint or None,
                    "error": str(exc),
                }
            )
            print(f"[smoke] failed {model_code}: {exc}", flush=True)

    report["status"] = "failed" if failed_models else "passed"
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 1 if failed_models else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        if LAST_REPORT is not None:
            LAST_REPORT["status"] = "failed"
            LAST_REPORT["failure"] = {
                "type": exc.__class__.__name__,
                "error": str(exc),
            }
            write_report(LAST_REPORT)
            print(json.dumps(LAST_REPORT, ensure_ascii=False, indent=2), flush=True)
        raise
