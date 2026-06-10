import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


class FakeUpload:
    """Minimal async stand-in for fastapi.UploadFile."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.filename = "big.docx"

    async def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)


@pytest.mark.asyncio
async def test_oversized_stream_aborts_with_413(tmp_path, monkeypatch):
    from fastapi import HTTPException
    import main as backend_main

    # avoid touching the real encryptor
    monkeypatch.setattr(
        backend_main.security_manager, "encrypt_file", lambda src, dst: None
    )

    oversized = FakeUpload(b"x" * (backend_main.MAX_UPLOAD_BYTES + 1))
    with pytest.raises(HTTPException) as exc_info:
        await backend_main.secure_file_upload(oversized, tmp_path / "out.bin")
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_at_limit_stream_is_accepted(tmp_path, monkeypatch):
    import main as backend_main

    called = {}
    monkeypatch.setattr(
        backend_main.security_manager,
        "encrypt_file",
        lambda src, dst: called.setdefault("ok", True),
    )

    exact = FakeUpload(b"x" * backend_main.MAX_UPLOAD_BYTES)
    await backend_main.secure_file_upload(exact, tmp_path / "out.bin")
    assert called.get("ok")  # F9: exactly-at-limit stays accepted
