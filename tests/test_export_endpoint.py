import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import main as backend_main


def test_export_text_cap_constant():
    assert backend_main.MAX_EXPORT_TEXT_BYTES == 1 * 1024 * 1024


def test_export_request_model_rejects_oversized_text():
    text = "అ" * (backend_main.MAX_EXPORT_TEXT_BYTES + 1)  # bytes > chars for Telugu
    assert len(text.encode("utf-8")) > backend_main.MAX_EXPORT_TEXT_BYTES
    assert backend_main.export_text_too_large(text) is True
    assert backend_main.export_text_too_large("చిన్న పాఠ్యం") is False
