# backend/http_utils.py
"""HTTP header helpers shared by download/export endpoints."""
import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def content_disposition(filename: str, default: str = "download") -> str:
    """Build an attachment Content-Disposition header that survives latin-1
    header encoding (RFC 6266 / RFC 5987).

    - `filename=` gets an ASCII-only fallback (transliterated where possible,
      otherwise stripped). Never uses str.isalnum(): Indic characters pass
      isalnum() but cannot be encoded as latin-1 and crash Starlette.
    - `filename*=UTF-8''...` carries the percent-encoded original name for
      modern clients.
    """
    # Strip any path components (defence in depth alongside existing checks)
    name = PureWindowsPath(PurePosixPath(filename or "").name).name

    # Transliterate what we can via NFKD decomposition, then drop non-ASCII
    ascii_raw = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )

    # Preserve the file extension separately so it isn't swallowed by strip
    suffix = PurePosixPath(name).suffix
    ascii_suffix = "".join(c for c in suffix if c.isascii() and c.isprintable() and c not in "/\\")

    ascii_stem = _SAFE_CHARS.sub("-", PurePosixPath(ascii_raw).stem).strip("-.")

    if ascii_stem:
        ascii_name = f"{ascii_stem}{ascii_suffix}"
    elif ascii_suffix:
        ascii_name = f"{default}{ascii_suffix}"
    else:
        ascii_name = default

    utf8_name = quote(name or ascii_name, safe="")
    return f"attachment; filename=\"{ascii_name[:120]}\"; filename*=UTF-8''{utf8_name}"
