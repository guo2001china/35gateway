from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import UserAccessContext, require_user_session
from app.api.deps import get_db
from app.api.openapi_responses import SESSION_AUTH_ERROR_RESPONSES, USER_AUTH_ERROR_RESPONSES
from app.core.config import settings
from app.core.console_urls import is_local_host, resolve_console_url
from app.api.schemas import (
    EmailCodeSendRequest,
    EmailCodeSendResponse,
    EmailLoginRequest,
    EmailLoginResponse,
    PasswordLoginRequest,
    PasswordLoginResponse,
    PasswordRegisterRequest,
    PasswordRegisterResponse,
    PhoneCodeSendRequest,
    PhoneCodeSendResponse,
    PhoneLoginRequest,
    PhoneLoginResponse,
    SessionLogoutResponse,
    SessionMeResponse,
)
from app.domains.platform.services.auth_sessions import SessionAuthService

router = APIRouter(prefix="/auth")


def _is_local_host(hostname: str) -> bool:
    return is_local_host(hostname)


def _console_login_url(request: Request) -> str:
    return resolve_console_url(request, "/login")


def _google_redirect_uri(request: Request) -> str:
    request_redirect_uri = f"{str(request.base_url).rstrip('/')}/auth/google/callback"
    configured = settings.google_auth_redirect_url.strip()
    if configured:
        request_host = (request.url.hostname or "").strip().lower()
        configured_host = (urlsplit(configured).hostname or "").strip().lower()
        if _is_local_host(request_host) and not _is_local_host(configured_host):
            return request_redirect_uri
        return configured
    return request_redirect_uri


@router.post(
    "/phone/send-code",
    status_code=status.HTTP_201_CREATED,
    summary="发送手机号验证码",
    response_model=PhoneCodeSendResponse,
)
def send_phone_code(payload: PhoneCodeSendRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).send_phone_code(phone=payload.phone)


@router.post(
    "/email/send-code",
    status_code=status.HTTP_201_CREATED,
    summary="发送邮箱验证码",
    response_model=EmailCodeSendResponse,
)
def send_email_code(payload: EmailCodeSendRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).send_email_code(email=payload.email)


@router.post(
    "/login/phone",
    status_code=status.HTTP_201_CREATED,
    summary="手机号验证码登录",
    response_model=PhoneLoginResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def login_with_phone(payload: PhoneLoginRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).login_with_phone(
        phone=payload.phone,
        code=payload.code,
        growth_context=payload.growth_context.model_dump(exclude_none=True) if payload.growth_context else None,
    )


@router.post(
    "/login/email",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱验证码登录",
    response_model=EmailLoginResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def login_with_email(payload: EmailLoginRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).login_with_email(
        email=payload.email,
        code=payload.code,
        growth_context=payload.growth_context.model_dump(exclude_none=True) if payload.growth_context else None,
    )


@router.post(
    "/login/password",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱密码登录",
    response_model=PasswordLoginResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def login_with_password(payload: PasswordLoginRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).login_with_password(
        email=payload.email,
        password=payload.password,
        growth_context=payload.growth_context.model_dump(exclude_none=True) if payload.growth_context else None,
    )


@router.post(
    "/register/password",
    status_code=status.HTTP_201_CREATED,
    summary="邮箱验证码注册并设置密码",
    response_model=PasswordRegisterResponse,
    responses=USER_AUTH_ERROR_RESPONSES,
)
def register_with_password(payload: PasswordRegisterRequest, db: Session = Depends(get_db)) -> dict:
    return SessionAuthService(db).register_with_password(
        email=payload.email,
        code=payload.code,
        password=payload.password,
        growth_context=payload.growth_context.model_dump(exclude_none=True) if payload.growth_context else None,
    )


@router.get(
    "/session/me",
    summary="获取当前浏览器会话",
    response_model=SessionMeResponse,
    responses=SESSION_AUTH_ERROR_RESPONSES,
)
def get_session_me(
    ctx: UserAccessContext = Depends(require_user_session),
    db: Session = Depends(get_db),
) -> dict:
    auth_service = SessionAuthService(db)
    session_record = auth_service.get_session_record(ctx.session_token or "")
    if session_record is None:
        raise HTTPException(status_code=401, detail="invalid_session_token")
    return auth_service.get_session_me(session_record=session_record)


@router.post(
    "/session/logout",
    summary="退出当前浏览器会话",
    response_model=SessionLogoutResponse,
    responses=SESSION_AUTH_ERROR_RESPONSES,
)
def logout_session(
    ctx: UserAccessContext = Depends(require_user_session),
    db: Session = Depends(get_db),
) -> dict:
    return {"revoked": SessionAuthService(db).revoke_session(token=ctx.session_token or "")}


@router.get("/google/url", summary="获取 Google 登录地址", include_in_schema=False)
def google_login_url(
    request: Request,
    next: str = Query(default="/"),
    db: Session = Depends(get_db),
) -> dict:
    auth_service = SessionAuthService(db)
    return {
        "provider": "google",
        "enabled": True,
        "url": auth_service.get_google_login_url(
            next_path=next,
            redirect_uri=_google_redirect_uri(request),
        ),
    }


@router.get("/google/start", summary="发起 Google 登录", include_in_schema=False)
def google_login_start(
    request: Request,
    next: str = Query(default="/"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    auth_service = SessionAuthService(db)
    login_url = auth_service.get_google_login_url(
        next_path=next,
        redirect_uri=_google_redirect_uri(request),
    )
    return RedirectResponse(login_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback", summary="Google 登录回调", include_in_schema=False)
def google_login_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    console_login_url = _console_login_url(request)
    auth_service = SessionAuthService(db)

    if error:
        fragment = auth_service.encode_console_hash(auth_error=error)
        return RedirectResponse(f"{console_login_url}#{fragment}", status_code=status.HTTP_302_FOUND)

    try:
        result = auth_service.login_with_google(
            code=code or "",
            state=state or "",
            redirect_uri=_google_redirect_uri(request),
        )
    except HTTPException as exc:
        fragment = auth_service.encode_console_hash(auth_error=str(exc.detail))
        return RedirectResponse(f"{console_login_url}#{fragment}", status_code=status.HTTP_302_FOUND)

    fragment = auth_service.encode_console_hash(
        session_token=result["session_token"],
        next_path=result["next_path"],
    )
    return RedirectResponse(f"{console_login_url}#{fragment}", status_code=status.HTTP_302_FOUND)


@router.get("/wechat/url", summary="获取微信登录地址", include_in_schema=False)
def wechat_login_url() -> dict:
    return {"provider": "wechat", "enabled": False, "message": "not_implemented"}
