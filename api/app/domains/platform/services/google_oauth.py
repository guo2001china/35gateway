from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuthService:
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
    scopes = "openid email profile"

    def __init__(self) -> None:
        self.client_id = settings.google_auth_client_id.strip()
        self.client_secret = settings.google_auth_client_secret.strip()

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def build_authorization_url(self, *, redirect_uri: str, state: str) -> str:
        if not self.is_configured():
            raise GoogleOAuthError("google_oauth_not_configured")

        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": self.scopes,
                "access_type": "online",
                "include_granted_scopes": "true",
                "prompt": "select_account",
                "state": state,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        if not self.is_configured():
            raise GoogleOAuthError("google_oauth_not_configured")

        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = httpx.post(self.token_endpoint, data=payload, timeout=10)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("google_oauth_token_request_failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise GoogleOAuthError("google_oauth_token_invalid_response") from exc

        if response.status_code >= 400:
            message = str(data.get("error") or data.get("error_description") or "google_oauth_token_failed")
            raise GoogleOAuthError(message)

        access_token = str(data.get("access_token") or "")
        if not access_token:
            raise GoogleOAuthError("google_oauth_access_token_missing")
        return data

    def fetch_userinfo(self, *, access_token: str) -> dict:
        try:
            response = httpx.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("google_oauth_userinfo_request_failed") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise GoogleOAuthError("google_oauth_userinfo_invalid_response") from exc

        if response.status_code >= 400:
            message = str(data.get("error") or "google_oauth_userinfo_failed")
            raise GoogleOAuthError(message)

        subject = str(data.get("sub") or "")
        email = str(data.get("email") or "").strip().lower()
        if not subject or not email:
            raise GoogleOAuthError("google_oauth_profile_incomplete")
        return data
