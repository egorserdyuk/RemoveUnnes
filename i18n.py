import gettext
from contextvars import ContextVar
from pathlib import Path

SUPPORTED = ("en", "ru")
DEFAULT = "en"
DOMAIN = "messages"
LOCALES_DIR = Path(__file__).parent / "locales"

_current: ContextVar[str] = ContextVar("locale", default=DEFAULT)

_translations: dict[str, gettext.NullTranslations] = {}
for _lang in SUPPORTED:
    try:
        _translations[_lang] = gettext.translation(DOMAIN, localedir=str(LOCALES_DIR), languages=[_lang])
    except OSError:
        _translations[_lang] = gettext.NullTranslations()


def set_lang(lang: str) -> None:
    _current.set(lang if lang in SUPPORTED else DEFAULT)


def get_lang() -> str:
    return _current.get()


def detect_language(tg_code: str | None) -> str:
    """Map a Telegram language_code to a supported locale."""
    if tg_code and tg_code.lower().startswith("ru"):
        return "ru"
    return DEFAULT


def _(msgid: str) -> str:
    return _translations[get_lang()].gettext(msgid)


def n(singular: str, plural: str, num: int) -> str:
    return _translations[get_lang()].ngettext(singular, plural, num)


async def activate_owner_lang(pool, tg_user) -> str:
    """Set request locale from stored owner lang, else Telegram language_code."""
    from db import get_owner_lang

    lang = await get_owner_lang(pool, tg_user.id)
    if lang is None:
        lang = detect_language(getattr(tg_user, "language_code", None))
    set_lang(lang)
    return lang
