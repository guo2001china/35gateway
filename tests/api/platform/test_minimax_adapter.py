from __future__ import annotations

import io
import tarfile

from app.domains.platform.providers.minimax import _unwrap_single_file_tar


def test_unwrap_single_file_tar_prefers_audio_member() -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        payload = b"ID3-demo-mp3"
        info = tarfile.TarInfo(name="audio.mp3")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    content, content_type = _unwrap_single_file_tar(buffer.getvalue(), "application/x-tar")
    assert content == b"ID3-demo-mp3"
    assert content_type == "audio/mpeg"


def test_unwrap_single_file_tar_keeps_non_tar_payload() -> None:
    content, content_type = _unwrap_single_file_tar(b"plain-bytes", "audio/mpeg")
    assert content == b"plain-bytes"
    assert content_type == "audio/mpeg"
