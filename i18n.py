from contextvars import ContextVar

from i18n_ru import RU_PLURALS, RU_STRINGS

SUPPORTED = ("en", "ru")
DEFAULT = "en"

_current: ContextVar[str] = ContextVar("locale", default=DEFAULT)


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
    if get_lang() == "ru":
        return RU_STRINGS.get(msgid, msgid)
    return msgid


def _ru_plural_index(num: int) -> int:
    if num % 10 == 1 and num % 100 != 11:
        return 0
    if 2 <= num % 10 <= 4 and (num % 100 < 10 or num % 100 >= 20):
        return 1
    return 2


def n(singular: str, plural: str, num: int) -> str:
    if get_lang() == "ru":
        forms = RU_PLURALS.get((singular, plural))
        if forms is not None:
            return forms[_ru_plural_index(num)]
    return singular if num == 1 else plural


async def activate_owner_lang(pool, tg_user) -> str:
    """Set request locale from stored owner lang, else Telegram language_code."""
    from db import get_owner_lang

    lang = await get_owner_lang(pool, tg_user.id)
    if lang is None:
        lang = detect_language(getattr(tg_user, "language_code", None))
    set_lang(lang)
    return lang
