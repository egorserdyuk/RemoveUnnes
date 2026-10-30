"""Pure helpers for per-chat per-type timing/rate limits.

Parsing: exact suffix input ``30s``/``1m``/``1h``/``1d`` (case-insensitive),
plus ``off``/``0``/empty to clear. Duration caps apply only to DURATION_TYPES;
cooldowns apply to all CONTENT_TYPES. Cooldown state itself lives in memory
in handlers_group (approach B); this module stays pure.
"""

import re
from datetime import datetime

DURATION_TYPES: set[str] = {"voice", "video", "video_note", "audio", "animation"}

_DURATION_FIELDS: tuple[str, ...] = ("voice", "video", "video_note", "audio", "animation")

_MULTIPLIERS: dict[str, int] = {"s": 1, "m": 60, "h": 3600, "d": 86400}

_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([smhdSMHD])\s*$")


def parse_window(s: str | None) -> int | None:
    """Parse a ``30s``-style window into seconds; ``off``/``0``/empty -> None."""
    if s is None:
        return None
    text = s.strip()
    if not text or text.lower() == "off" or text == "0":
        return None
    m = _WINDOW_RE.match(s)
    if not m:
        raise ValueError(f"bad window value: {s!r}")
    return int(m.group(1)) * _MULTIPLIERS[m.group(2).lower()]


def format_window(sec: int | None) -> str:
    """Format seconds back to ``30s``-style; None/non-positive -> ``off``."""
    if sec is None or sec <= 0:
        return "off"
    for suffix, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec % size == 0:
            return f"{sec // size}{suffix}"
    return f"{sec}s"


def get_duration(fields) -> int | None:
    """Extract Telegram ``duration`` (int seconds) from media fields, else None."""
    for attr in _DURATION_FIELDS:
        media = getattr(fields, attr, None)
        if media is None:
            continue
        if isinstance(media, dict):
            raw = media.get("duration")
        else:
            raw = getattr(media, "duration", None)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def is_duration_ok(dur: int | None, max_dur: int | None) -> bool:
    """True unless a known duration exceeds the cap."""
    if dur is None or max_dur is None:
        return True
    return dur <= max_dur


def is_cooldown_ok(now: datetime, last: datetime | None, cooldown_sec: int | None) -> bool:
    """True unless the last pass for this bucket is still inside the window."""
    if cooldown_sec is None or last is None:
        return True
    return (now - last).total_seconds() >= cooldown_sec
