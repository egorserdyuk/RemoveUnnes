import ast
from pathlib import Path

import i18n
from i18n import DEFAULT, detect_language
from i18n_ru import RU_PLURALS, RU_STRINGS

SOURCES = [
    "bot.py",
    "config.py",
    "db.py",
    "classify.py",
    "keyboards.py",
    "texts.py",
    "notices.py",
    "handlers_private.py",
    "handlers_group.py",
    "handlers_membership.py",
    "handlers_whitelist.py",
    "i18n.py",
]


def teardown_function():
    i18n.set_lang(DEFAULT)


def test_detect_language():
    assert detect_language("ru") == "ru"
    assert detect_language("ru-RU") == "ru"
    assert detect_language("en") == "en"
    assert detect_language(None) == "en"
    assert detect_language("de") == "en"


def test_unknown_lang_falls_back_to_default():
    i18n.set_lang("de")
    assert i18n.get_lang() == "en"


def test_english_returns_msgid():
    i18n.set_lang("en")
    assert i18n._("Hello") == "Hello"


def test_russian_translates_known_strings():
    i18n.set_lang("ru")
    assert i18n._("Stats") == "Статистика"
    assert i18n._("Hello") == "Hello"  # untranslated -> English fallback


def test_russian_plural_forms():
    i18n.set_lang("ru")
    n = i18n.n("{n} sticker", "{n} stickers", 1)
    assert n == "{n} стикер"
    assert i18n.n("{n} sticker", "{n} stickers", 3) == "{n} стикера"
    assert i18n.n("{n} sticker", "{n} stickers", 5) == "{n} стикеров"
    assert i18n.n("{n} sticker", "{n} stickers", 11) == "{n} стикеров"
    assert i18n.n("{n} sticker", "{n} stickers", 21) == "{n} стикер"
    assert i18n.n("{n} sticker", "{n} stickers", 22) == "{n} стикера"


def _literal_call_strings():
    """All string literals passed directly to _()/n() in sources."""
    singulars, pairs = set(), set()
    for src in SOURCES:
        tree = ast.parse(Path(src).read_text(), filename=src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            args = [a.value for a in node.args if isinstance(a, ast.Constant)]
            if node.func.id == "_" and len(args) >= 1 and isinstance(args[0], str):
                singulars.add(args[0])
            elif node.func.id == "n" and len(args) >= 2:
                pairs.add((args[0], args[1]))
    return singulars, pairs


def test_all_literal_msgids_covered():
    singulars, pairs = _literal_call_strings()
    assert singulars, "scanner found nothing — check SOURCES"
    assert singulars - set(RU_STRINGS) == set()
    assert {p for p in pairs if p not in RU_PLURALS} == set()


def test_dynamic_lists_registered():
    import notices
    from db import STAT_FORMS

    assert set(notices.INSULTS) - set(RU_STRINGS) == set()
    assert set(notices.NOTICE_TEMPLATES) - set(RU_STRINGS) == set()
    assert set(notices.CONTENT_LABELS.values()) - set(RU_STRINGS) == set()
    assert "someone" in RU_STRINGS
    assert {p for p in STAT_FORMS.values() if p not in RU_PLURALS} == set()


def test_russian_end_to_end():
    i18n.set_lang("ru")
    from db import format_stats

    assert format_stats({"sticker": 5, "photo": 1}) == "удалённые сообщения: 1 фото; 5 стикеров"
    import notices

    text = notices.render_notice("@bob", "voice", rng=lambda s: s[0])
    assert text == notices.RUSSIAN_REPLIES[0].format(user="@bob")
