"""Auth header for the WhatsApp bridge control API (/send, /simulate, /cache/invalidate).

The token is read from WHATSAPP_INGEST_TOKEN, falling back to the project .env so
host-side test scripts work without exporting it manually.
"""
import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def bridge_token() -> str:
    token = os.getenv("WHATSAPP_INGEST_TOKEN", "")
    if token or not _ENV_FILE.exists():
        return token
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == "WHATSAPP_INGEST_TOKEN":
            return value.strip().strip('"').strip("'")
    return ""


def bridge_headers(extra=None) -> dict:
    headers = {"X-NexaServe-Webhook-Token": bridge_token()}
    headers.update(extra or {})
    return headers
