#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "api"
DEFAULT_SMOKE_DB_PATH = BACKEND_ROOT / "data" / "provider-chain-mixed-smoke.sqlite3"


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
from tests.live.public_model_live_smoke import (  # noqa: E402
    create_temp_user_session,
    ensure_smoke_balance,
    fetch_system_default_api_key,
    iso_now,
)


BOOTSTRAP_PATH = BACKEND_ROOT / "app" / "domains" / "platform" / "services" / "platform_bootstrap_data.json"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "output" / "live"
OUTPUT_PATH = OUTPUT_DIR / "provider-chain-mixed-smoke-report.json"
SUPPORTED_ROUTE_GROUPS = {"openai", "responses", "gemini"}
PROVIDER_ENV_FALLBACKS: dict[str, dict[str, str]] = {
    "yunwu_openai": {
        "api_key": "API35_YUNWU_OPENAI_API_KEY",
        "base_url": "API35_YUNWU_OPENAI_BASE_URL",
    },
    "openrouter": {
        "api_key": "OPENROUTER_API_KEY",
        "base_url": "OPENROUTER_BASE_URL",
    },
    "openai_official": {
        "api_key": "API35_OPENAI_OFFICIAL_API_KEY",
        "base_url": "API35_OPENAI_OFFICIAL_BASE_URL",
    },
}


@dataclass
class RouteCase:
    model_code: str
    route_group: str
    endpoint: str
    selected: bool
    skip_reason: str | None = None


def _load_bootstrap() -> dict[str, Any]:
    return json.loads(BOOTSTRAP_PATH.read_text(encoding="utf-8"))


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


def _build_case_matrix(*, primary_provider: str, fallback_provider: str) -> tuple[list[RouteCase], dict[str, Any]]:
    payload = _load_bootstrap()
    public_routes = {
        (str(route["model_code"]), str(route["route_group"])): route
        for route in payload["routes"]
        if route.get("public_api_visible")
    }

    bindings_by_route: dict[tuple[str, str], set[str]] = defaultdict(set)
    for binding in payload["provider_bindings"]:
        if not binding.get("enabled", True):
            continue
        key = (str(binding["model_code"]), str(binding["route_group"]))
        if key in public_routes:
            bindings_by_route[key].add(str(binding["provider_code"]))

    route_groups = sorted({str(route["route_group"]) for route in public_routes.values()})
    mixed_candidates: dict[str, list[tuple[str, str]]] = defaultdict(list)
    cases: list[RouteCase] = []
    summary: dict[str, Any] = {
        "primary_provider": primary_provider,
        "fallback_provider": fallback_provider,
        "route_groups": {},
    }

    preferred_representatives = {
        "seedance": "seedance-2.0-fast",
        "banana": "nano-banana",
        "seedream": "doubao-seedream-5.0-lite",
        "qwen_tts": "qwen3-tts-flash",
        "minimax_t2a_async": "speech-2.8-turbo",
        "veo3": "veo-3-fast",
        "veo31": "veo-3.1-fast",
        "wan_video": "wan2.6-flash",
        "minimax_video": "minimax-hailuo-2.3-fast",
        "vidu": "viduq3-turbo",
    }

    for key, route in sorted(public_routes.items()):
        model_code, route_group = key
        provider_codes = bindings_by_route.get(key, set())
        endpoint = str((route.get("endpoints_json") or {}).get("create") or "")
        if primary_provider in provider_codes and fallback_provider in provider_codes:
            mixed_candidates[route_group].append((model_code, endpoint))
            continue

        skip_reason = None
        if fallback_provider not in provider_codes:
            skip_reason = "missing_fallback_binding"
        elif primary_provider not in provider_codes:
            skip_reason = "missing_primary_binding"
        elif route_group not in SUPPORTED_ROUTE_GROUPS:
            skip_reason = "unsupported_route_group"
        cases.append(
            RouteCase(
                model_code=model_code,
                route_group=route_group,
                endpoint=endpoint,
                selected=False,
                skip_reason=skip_reason or "not_selected",
            )
        )

    for route_group in route_groups:
        selected_models: list[str] = []
        skipped_models: list[str] = []
        candidates = sorted(mixed_candidates.get(route_group, []), key=lambda item: item[0])
        if not candidates:
            summary["route_groups"][route_group] = {
                "status": "skipped",
                "reason": "no_dual_binding",
                "selected_models": [],
            }
            continue

        if route_group not in SUPPORTED_ROUTE_GROUPS:
            preferred = preferred_representatives.get(route_group)
            selected = None
            if preferred:
                selected = next((item for item in candidates if item[0] == preferred), None)
            if selected is None:
                selected = candidates[0]
            selected_set = {selected[0]}
        else:
            selected_set = {model_code for model_code, _ in candidates}

        for model_code, endpoint in candidates:
            if model_code in selected_set:
                cases.append(RouteCase(model_code=model_code, route_group=route_group, endpoint=endpoint, selected=True))
                selected_models.append(model_code)
            else:
                cases.append(
                    RouteCase(
                        model_code=model_code,
                        route_group=route_group,
                        endpoint=endpoint,
                        selected=False,
                        skip_reason="covered_by_route_group_representative",
                    )
                )
                skipped_models.append(model_code)

        summary["route_groups"][route_group] = {
            "status": "selected",
            "selected_models": selected_models,
            "skipped_models": skipped_models,
        }

    return cases, summary


def _build_payload(case: RouteCase) -> tuple[dict[str, Any], str]:
    expected = f"MIXED-SMOKE-{case.model_code}"
    if case.route_group in {"openai", "gemini"}:
        return {
            "model": case.model_code,
            "messages": [{"role": "user", "content": f"reply exactly: {expected}"}],
            "max_tokens": 16,
        }, expected
    if case.route_group == "responses":
        return {
            "model": case.model_code,
            "input": f"reply exactly: {expected}",
            "max_output_tokens": 16,
        }, expected
    raise AssertionError(f"unsupported mixed smoke route group: {case.route_group}")


def _extract_text_content(route_group: str, payload: dict[str, Any]) -> str:
    if route_group in {"openai", "gemini"}:
        return str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
    if route_group == "responses":
        output_text = str(payload.get("output_text") or "").strip()
        if output_text:
            return output_text
        output = payload.get("output") or []
        chunks: list[str] = []
        for item in output:
            for content in item.get("content") or []:
                text = str(content.get("text") or "").strip()
                if text:
                    chunks.append(text)
        return "\n".join(chunks).strip()
    return ""


def _poll_new_request(*, user_id: int, after_id: int, timeout_seconds: int = 15) -> Request:
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


def _prepare_user_provider_account(
    client: TestClient,
    *,
    session_token: str,
    user_id: int,
    primary_provider: str,
) -> dict[str, Any]:
    provider = get_provider(primary_provider)
    local_env = _load_local_env()
    env_mapping = PROVIDER_ENV_FALLBACKS.get(primary_provider, {})

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
        base_url_override = str(os.getenv(base_url_env or "", "") or local_env.get(base_url_env or "", "")).strip()

    if not credential_payload:
        raise AssertionError(f"provider {primary_provider} has no configured auth in current env")

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise AssertionError(f"user not found: {user_id}")
        user.balance = Decimal("100")
        db.query(ProviderAccount).filter(
            ProviderAccount.user_id == user_id,
            ProviderAccount.provider_code == primary_provider,
        ).delete(synchronize_session=False)
        db.commit()

    payload = {
        "provider_code": primary_provider,
        "display_name": f"{primary_provider} mixed smoke",
        "base_url_override": base_url_override or None,
        "credential_payload": credential_payload,
        "priority": 10,
    }
    resp = client.post(
        "/v1/provider-accounts",
        headers={"Authorization": f"Bearer {session_token}"},
        json=payload,
    )
    if resp.status_code not in (200, 201):
        raise AssertionError(f"provider account create failed: status={resp.status_code} body={resp.text}")
    return resp.json()


def write_report(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mixed-provider smoke matrix against configured providers.")
    parser.add_argument("--primary-provider", default="yunwu_openai")
    parser.add_argument("--fallback-provider", default="35m")
    args = parser.parse_args()

    cases, matrix_summary = _build_case_matrix(
        primary_provider=args.primary_provider,
        fallback_provider=args.fallback_provider,
    )

    app = create_app()
    with TestClient(app) as client:
        backend_url = "http://testserver"
        smoke_user = create_temp_user_session(client, backend_url)
        user_id = int(smoke_user["user"]["user_id"])
        session_token = str(smoke_user["session_token"])
        ensure_smoke_balance(user_id, minimum_balance=Decimal("100"))
        provider_account = _prepare_user_provider_account(
            client,
            session_token=session_token,
            user_id=user_id,
            primary_provider=args.primary_provider,
        )
        system_api_key = fetch_system_default_api_key(client, backend_url, session_token)

        results: list[dict[str, Any]] = []
        for case in cases:
            if not case.selected:
                results.append(
                    {
                        "model_code": case.model_code,
                        "route_group": case.route_group,
                        "status": "skipped",
                        "skip_reason": case.skip_reason,
                    }
                )
                continue

            payload, expected = _build_payload(case)
            with SessionLocal() as db:
                before_request_id = int(db.query(Request.id).order_by(Request.id.desc()).first()[0] or 0) if db.query(Request.id).first() else 0
            headers = {
                "Authorization": f"Bearer {system_api_key}",
                "X-API35-Chain": f"{args.primary_provider},{args.fallback_provider}",
            }
            path = case.endpoint.replace("POST ", "").replace("GET ", "")
            response = client.post(path, headers=headers, json=payload)
            request_row = _poll_new_request(user_id=user_id, after_id=before_request_id)
            provider_attempts = _fetch_provider_attempts(request_row.id)

            body = response.json() if "application/json" in response.headers.get("content-type", "") else {"raw": response.text[:500]}
            content = _extract_text_content(case.route_group, body if isinstance(body, dict) else {})
            outcome = "failed"
            if provider_attempts:
                first = provider_attempts[0]
                if (
                    first.provider_code == args.primary_provider
                    and first.status == "succeeded"
                    and len(provider_attempts) == 1
                ):
                    outcome = "primary_succeeded"
                elif any(
                    row.provider_code == args.fallback_provider and row.status == "succeeded"
                    for row in provider_attempts
                ):
                    outcome = "fallback_succeeded"

            result_status = "passed"
            failure_reason = None
            if response.status_code not in (200, 201):
                result_status = "failed"
                failure_reason = f"http_{response.status_code}"
            elif not content or expected not in content:
                result_status = "failed"
                failure_reason = "content_assertion_failed"

            results.append(
                {
                    "model_code": case.model_code,
                    "route_group": case.route_group,
                    "status": result_status,
                    "outcome": outcome,
                    "expected": expected,
                    "content": content,
                    "failure_reason": failure_reason,
                    "request_id": request_row.request_id,
                    "route_plan": request_row.route_plan,
                    "provider_attempts": [
                        {
                            "provider_code": row.provider_code,
                            "owner_type": row.provider_account_owner_type,
                            "status": row.status,
                            "http_status": row.http_status_code,
                            "error": row.error_message,
                        }
                        for row in provider_attempts
                    ],
                }
            )

    summary = {
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
    }
    report = {
        "generated_at": iso_now(),
        "primary_provider": args.primary_provider,
        "fallback_provider": args.fallback_provider,
        "provider_account_id": provider_account.get("id"),
        "matrix": matrix_summary,
        "summary": summary,
        "results": results,
    }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
