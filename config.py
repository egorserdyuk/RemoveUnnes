"""Runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str
    dsn: str
    api_base: str | None = None


def load() -> Settings:
    token = os.environ.get("BOT_TOKEN", "").strip()
    dsn = os.environ.get("POSTGRES_DSN", "").strip()
    api_base = os.environ.get("TELEGRAM_API_URL", "").strip() or None
    missing = [name for name, v in (("BOT_TOKEN", token), ("POSTGRES_DSN", dsn)) if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return Settings(token=token, dsn=dsn, api_base=api_base)
