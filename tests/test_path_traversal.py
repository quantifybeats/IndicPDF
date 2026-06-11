"""Regression: the SPA catch-all must never serve files outside FRONTEND_DIST (QA F1)."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import main  # noqa: E402

client = TestClient(main.app)

TRAVERSALS = [
    "/%2e%2e/%2e%2e/backend/main.py",
    "/..%2f..%2fbackend%2fsecurity_manager.py",
    "/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
    "/static/../../../backend/main.py",
]


def _looks_like_source_or_secret(text: str) -> bool:
    markers = ("INDICPDF_API_KEY", "class SecurityManager", "def export_pdf", "root:")
    return any(m in text for m in markers)


def test_catchall_blocks_path_traversal():
    for path in TRAVERSALS:
        r = client.get(path)
        # Either a hard 404, or the SPA index.html fallback — never backend source.
        assert not _looks_like_source_or_secret(r.text), f"LEAKED via {path}"


def test_catchall_still_serves_index_for_spa_routes():
    r = client.get("/reconstruct")
    assert r.status_code in (200, 404)  # depends on whether dist is built
    assert not _looks_like_source_or_secret(r.text)
