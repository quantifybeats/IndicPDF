"""Shared pytest setup.

The unit suite runs everything in a single process, so an ephemeral AES key
is fine. Opt into it before any backend module imports SecurityManager, so the
production fail-fast guard (missing INDICPDF_MASTER_KEY) does not trip during
test collection.
"""
import os

os.environ.setdefault("INDICPDF_ALLOW_EPHEMERAL_KEY", "1")
