"""Load configuration from .env (no external dependencies)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def cors_origins() -> str:
    return get("CORS_ORIGINS", "*")


def agent_api_key() -> str:
    return get("AGENT_API_KEY", "")


def agent_public_url() -> str:
    return get("AGENT_PUBLIC_URL", "").rstrip("/")


def agent_port() -> int:
    try:
        return int(get("AGENT_PORT", "8765"))
    except ValueError:
        return 8765


def agent_host() -> str:
    return get("AGENT_HOST", "0.0.0.0")
