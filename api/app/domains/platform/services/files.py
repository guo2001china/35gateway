from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import mimetypes
import re
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, unquote, urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.platform.entities.entities import StoredFile, User


def _utc_iso8601_from_now(seconds: int) -> str:
    return datetime.fromtimestamp(time.time() + seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "file"


class FileService:
    def __init__(self, db: Session):
        self.db = db

    def _require_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        if user.status != "active":
            raise HTTPException(status_code=403, detail="user_not_active")
        return user

    def _require_oss_ready(self) -> None:
        if not all(
            [
                settings.oss_bucket,
                settings.oss_endpoint,
                settings.oss_access_key_id,
                settings.oss_access_key_secret,
            ]
        ):
            raise HTTPException(status_code=503, detail="oss_not_configured")

    def _build_upload_host(self) -> str:
        endpoint = settings.oss_endpoint.strip().rstrip("/")
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            endpoint = endpoint.split("://", 1)[1]
        return f"https://{settings.oss_bucket}.{endpoint}"

    def _normalize_content_type(self, content_type: str | None) -> str | None:
        if content_type is None:
            return None
        normalized = content_type.split(";", 1)[0].strip().lower()
        return normalized or None

    def _ensure_public_ip(self, host_ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        if not host_ip.is_global:
            raise HTTPException(status_code=422, detail="remote_host_not_public")

    def _ensure_public_host(self, url: str) -> None:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise HTTPException(status_code=422, detail="unsupported_url_scheme")
        if parsed.username or parsed.password:
            raise HTTPException(status_code=422, detail="invalid_remote_url")
        if not parsed.hostname:
            raise HTTPException(status_code=422, detail="invalid_remote_url")

        host = parsed.hostname.strip().lower()
        if not host or host == "localhost":
            raise HTTPException(status_code=422, detail="remote_host_not_public")

        try:
            host_ip = ipaddress.ip_address(host)
        except ValueError:
            try:
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="invalid_remote_url") from exc
            try:
                addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise HTTPException(status_code=422, detail="remote_host_unresolvable") from exc
            if not addresses:
                raise HTTPException(status_code=422, detail="remote_host_unresolvable")
            for _, _, _, _, sockaddr in addresses:
                resolved_ip = sockaddr[0].split("%", 1)[0]
                self._ensure_public_ip(ipaddress.ip_address(resolved_ip))
            return

        self._ensure_public_ip(host_ip)

    def _parse_content_length(self, value: str | None) -> int | None:
        if value is None:
            return None
        try:
            length = int(value)
        except ValueError:
            return None
        return length if length >= 0 else None

    def _extract_filename_from_content_disposition(self, content_disposition: str | None) -> str | None:
        if not content_disposition:
            return None
        utf8_match = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", content_disposition, flags=re.IGNORECASE)
        if utf8_match:
            filename = unquote(utf8_match.group(1).strip())
            return filename or None
        plain_match = re.search(r'filename\s*=\s*"?(?P<filename>[^";]+)"?', content_disposition, flags=re.IGNORECASE)
        if plain_match:
            filename = plain_match.group("filename").strip()
            return filename or None
        return None

    def _filename_from_url(self, url: str) -> str | None:
        path = urlsplit(url).path
        if not path:
            return None
        candidate = unquote(path.rsplit("/", 1)[-1]).strip()
        return candidate or None

    def _default_filename(self, content_type: str) -> str:
        extension = mimetypes.guess_extension(content_type) or ""
        return f"file{extension}"

    def _resolve_import_content_type(
        self,
        *,
        requested_content_type: str | None,
        remote_content_type: str | None,
        filename: str | None,
    ) -> str:
        requested = self._normalize_content_type(requested_content_type)
        remote = self._normalize_content_type(remote_content_type)

        if remote == "text/html":
            raise HTTPException(status_code=422, detail="remote_content_type_mismatch")

        if requested is not None:
            requested_kind = self._guess_kind_from_content_type(requested)
            if remote is not None:
                try:
                    remote_kind = self._guess_kind_from_content_type(remote)
                except HTTPException:
                    remote_kind = None
                if remote_kind is not None and remote_kind != requested_kind:
                    raise HTTPException(status_code=422, detail="remote_content_type_mismatch")
            return requested

        if remote is not None:
            self._guess_kind_from_content_type(remote)
            return remote

        guessed = self._normalize_content_type(mimetypes.guess_type(filename or "")[0])
        if guessed is None:
            raise HTTPException(status_code=422, detail="missing_content_type")
        self._guess_kind_from_content_type(guessed)
        return guessed

    def _resolve_import_filename(
        self,
        *,
        requested_filename: str | None,
        response: httpx.Response,
        content_type: str,
    ) -> str:
        if requested_filename and requested_filename.strip():
            return requested_filename.strip()

        content_disposition_filename = self._extract_filename_from_content_disposition(
            response.headers.get("content-disposition")
        )
        if content_disposition_filename:
            return content_disposition_filename

        url_filename = self._filename_from_url(str(response.url))
        if url_filename:
            return url_filename

        return self._default_filename(content_type)

    def _download_remote_file(
        self,
        *,
        url: str,
        filename: str | None,
        content_type: str | None,
    ) -> tuple[str, str, bytes]:
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)
        redirect_statuses = {301, 302, 303, 307, 308}
        current_url = url.strip()

        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            for redirect_count in range(4):
                self._ensure_public_host(current_url)
                try:
                    with client.stream("GET", current_url, headers={"Accept": "*/*"}) as response:
                        if response.status_code in redirect_statuses:
                            location = response.headers.get("location")
                            if not location:
                                raise HTTPException(status_code=502, detail="remote_file_download_failed")
                            if redirect_count >= 3:
                                raise HTTPException(status_code=502, detail="remote_file_too_many_redirects")
                            current_url = str(response.url.join(location))
                            continue

                        response.raise_for_status()

                        remote_content_type = response.headers.get("content-type")
                        resolved_content_type = self._resolve_import_content_type(
                            requested_content_type=content_type,
                            remote_content_type=remote_content_type,
                            filename=filename,
                        )
                        resolved_filename = self._resolve_import_filename(
                            requested_filename=filename,
                            response=response,
                            content_type=resolved_content_type,
                        )
                        declared_size = self._parse_content_length(response.headers.get("content-length"))
                        if declared_size is not None and declared_size > settings.oss_max_file_size:
                            raise HTTPException(status_code=422, detail="file_too_large")

                        content_buffer = bytearray()
                        for chunk in response.iter_bytes():
                            if not chunk:
                                continue
                            content_buffer.extend(chunk)
                            if len(content_buffer) > settings.oss_max_file_size:
                                raise HTTPException(status_code=422, detail="file_too_large")

                        if not content_buffer:
                            raise HTTPException(status_code=422, detail="empty_file")
                        return resolved_filename, resolved_content_type, bytes(content_buffer)
                except HTTPException:
                    raise
                except httpx.HTTPError as exc:
                    raise HTTPException(status_code=502, detail="remote_file_download_failed") from exc

        raise HTTPException(status_code=502, detail="remote_file_download_failed")

    def _build_object_key(self, *, user_id: int, file_id: str, filename: str) -> str:
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        safe_filename = _sanitize_filename(filename)
        prefix = settings.oss_key_prefix.strip("/")
        return f"{prefix}/{user_id}/{date_prefix}/{file_id}_{safe_filename}"

    def _sign_policy(self, policy_b64: str) -> str:
        digest = hmac.new(
            settings.oss_access_key_secret.encode("utf-8"),
            policy_b64.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _guess_kind_from_content_type(self, content_type: str) -> str:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/"):
            return "audio"
        raise HTTPException(status_code=422, detail="unsupported_file_content_type")

    def _content_prefix_for_kind(self, kind: str) -> str:
        if kind == "image":
            return "image/"
        if kind == "video":
            return "video/"
        if kind == "audio":
            return "audio/"
        raise HTTPException(status_code=422, detail="unsupported_file_kind")

    def _build_signed_url(
        self,
        *,
        object_key: str,
        expires_in: int | None = None,
        method: str = "GET",
    ) -> str:
        self._require_oss_ready()
        expires = int(time.time() + (expires_in or settings.oss_signed_url_expire_seconds))
        canonical_resource = f"/{settings.oss_bucket}/{object_key}"
        string_to_sign = f"{method.upper()}\n\n\n{expires}\n{canonical_resource}"
        digest = hmac.new(
            settings.oss_access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = quote(base64.b64encode(digest).decode("utf-8"), safe="")
        return (
            f"{self._build_upload_host()}/{quote(object_key, safe='/')}"
            f"?OSSAccessKeyId={quote(settings.oss_access_key_id, safe='')}"
            f"&Expires={expires}"
            f"&Signature={signature}"
        )

    def _upload_with_policy(
        self,
        *,
        upload_url: str,
        object_key: str,
        policy: str,
        signature: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> str | None:
        timeout = httpx.Timeout(60.0)
        data = {
            "key": object_key,
            "policy": policy,
            "OSSAccessKeyId": settings.oss_access_key_id,
            "Signature": signature,
            "success_action_status": "200",
            "Content-Type": content_type,
        }
        files = {
            "file": (filename, content, content_type),
        }
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.post(upload_url, data=data, files=files)
                response.raise_for_status()
                return response.headers.get("etag")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="oss_upload_failed") from exc

    def create_upload_policy(
        self,
        *,
        user_id: int,
        filename: str,
        content_type: str,
        size: int | None = None,
    ) -> dict[str, Any]:
        self._require_user(user_id)
        self._require_oss_ready()
        if size is not None and size <= 0:
            raise HTTPException(status_code=422, detail="invalid_file_size")
        if size is not None and size > settings.oss_max_file_size:
            raise HTTPException(status_code=422, detail="file_too_large")

        kind = self._guess_kind_from_content_type(content_type)
        file_id = f"file_{uuid.uuid4().hex[:24]}"
        object_key = self._build_object_key(user_id=user_id, file_id=file_id, filename=filename)
        stored_file = StoredFile(
            file_id=file_id,
            user_id=user_id,
            bucket=settings.oss_bucket,
            object_key=object_key,
            filename=_sanitize_filename(filename),
            content_type=content_type,
            size=size,
            kind=kind,
            status="pending",
        )
        self.db.add(stored_file)
        self.db.commit()
        self.db.refresh(stored_file)

        expiration = _utc_iso8601_from_now(settings.oss_upload_expire_seconds)
        content_prefix = self._content_prefix_for_kind(kind)
        policy_dict = {
            "expiration": expiration,
            "conditions": [
                {"bucket": settings.oss_bucket},
                {"key": object_key},
                {"success_action_status": "200"},
                ["content-length-range", 1, settings.oss_max_file_size],
                ["starts-with", "$Content-Type", content_prefix],
            ],
        }
        policy_b64 = base64.b64encode(json.dumps(policy_dict).encode("utf-8")).decode("utf-8")
        signature = self._sign_policy(policy_b64)
        return {
            "file_id": stored_file.file_id,
            "bucket": settings.oss_bucket,
            "endpoint": settings.oss_endpoint,
            "object_key": object_key,
            "upload_url": self._build_upload_host(),
            "policy": policy_b64,
            "signature": signature,
            "access_key_id": settings.oss_access_key_id,
            "expire_at": expiration,
            "max_size": settings.oss_max_file_size,
            "allowed_content_types": [content_prefix],
            "success_action_status": "200",
        }

    def complete_upload(
        self,
        *,
        user_id: int,
        file_id: str,
        size: int,
        content_type: str,
        etag: str | None = None,
    ) -> dict[str, Any]:
        self._require_user(user_id)
        stored_file = (
            self.db.query(StoredFile)
            .filter(StoredFile.file_id == file_id, StoredFile.user_id == user_id)
            .first()
        )
        if stored_file is None:
            raise HTTPException(status_code=404, detail="file_not_found")
        if size <= 0:
            raise HTTPException(status_code=422, detail="invalid_file_size")
        if size > settings.oss_max_file_size:
            raise HTTPException(status_code=422, detail="file_too_large")
        kind = self._guess_kind_from_content_type(content_type)
        if stored_file.kind != kind:
            raise HTTPException(status_code=422, detail="file_kind_mismatch")

        signed_url = self._build_signed_url(
            object_key=stored_file.object_key,
            expires_in=300,
            method="HEAD",
        )
        timeout = httpx.Timeout(20.0)
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.head(signed_url)
                response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail="oss_file_verify_failed") from exc

        stored_file.size = size
        stored_file.content_type = content_type
        stored_file.status = "uploaded"
        stored_file.completed_at = datetime.now(timezone.utc)
        self.db.add(stored_file)
        self.db.commit()
        self.db.refresh(stored_file)
        return self.serialize_file(stored_file, etag=etag)

    def upload_file(
        self,
        *,
        user_id: int,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        if not content:
            raise HTTPException(status_code=422, detail="empty_file")
        self._require_user(user_id)

        policy = self.create_upload_policy(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size=len(content),
        )
        etag = self._upload_with_policy(
            upload_url=policy["upload_url"],
            object_key=policy["object_key"],
            policy=policy["policy"],
            signature=policy["signature"],
            filename=filename,
            content_type=content_type,
            content=content,
        )
        return self.complete_upload(
            user_id=user_id,
            file_id=policy["file_id"],
            size=len(content),
            content_type=content_type,
            etag=etag,
        )

    def import_file_from_url(
        self,
        *,
        user_id: int,
        url: str,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        self._require_user(user_id)
        self._require_oss_ready()

        resolved_filename, resolved_content_type, content_bytes = self._download_remote_file(
            url=url,
            filename=filename,
            content_type=content_type,
        )
        return self.upload_file(
            user_id=user_id,
            filename=resolved_filename,
            content_type=resolved_content_type,
            content=content_bytes,
        )

    def list_files(
        self,
        *,
        user_id: int,
        page: int = 1,
        size: int = 20,
        kind: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        self._require_user(user_id)
        if page < 1:
            raise HTTPException(status_code=422, detail="invalid_page")
        if size < 1 or size > 100:
            raise HTTPException(status_code=422, detail="invalid_page_size")
        normalized_kind = kind.strip().lower() if kind else None
        if normalized_kind not in {None, "image", "video", "audio"}:
            raise HTTPException(status_code=422, detail="invalid_file_kind")

        query = self.db.query(StoredFile).filter(StoredFile.user_id == user_id)
        if normalized_kind is not None:
            query = query.filter(StoredFile.kind == normalized_kind)

        total = query.count()
        rows = query.order_by(StoredFile.id.desc()).offset((page - 1) * size).limit(size).all()
        return total, [self.serialize_file(row) for row in rows]

    def get_file(self, *, user_id: int, file_id: str) -> dict[str, Any]:
        self._require_user(user_id)
        stored_file = (
            self.db.query(StoredFile)
            .filter(StoredFile.file_id == file_id, StoredFile.user_id == user_id)
            .first()
        )
        if stored_file is None:
            raise HTTPException(status_code=404, detail="file_not_found")
        return self.serialize_file(stored_file)

    def serialize_file(self, stored_file: StoredFile, *, etag: str | None = None) -> dict[str, Any]:
        return {
            "file_id": stored_file.file_id,
            "filename": stored_file.filename,
            "content_type": stored_file.content_type,
            "size": stored_file.size,
            "kind": stored_file.kind,
            "status": stored_file.status,
            "bucket": stored_file.bucket,
            "object_key": stored_file.object_key,
            "url": self._build_signed_url(object_key=stored_file.object_key) if stored_file.status == "uploaded" else None,
            "etag": etag,
            "created_at": stored_file.created_at.isoformat() if stored_file.created_at is not None else None,
            "completed_at": stored_file.completed_at.isoformat() if stored_file.completed_at is not None else None,
        }
