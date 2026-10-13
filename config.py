"""Runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str
    dsn: str


def load() -> Settings:
    token = os.environ.get("BOT_TOKEN", "").strip()
    dsn = os.environ.get("POSTGRES_DSN", "").strip()
    missing = [name for name, v in (("BOT_TOKEN", token), ("POSTGRES_DSN", dsn)) if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return Settings(token=token, dsn=dsn)
