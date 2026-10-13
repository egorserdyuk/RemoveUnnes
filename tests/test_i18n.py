import i18n
from i18n import DEFAULT, detect_language


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


def test_russian_placeholder_falls_back_to_english():
    # ru catalog exists but translations are placeholders (empty) for now.
    i18n.set_lang("ru")
    assert i18n._("Hello") == "Hello"


def test_ru_catalog_covers_all_msgids():
    from babel.messages.pofile import read_po

    with open("locales/messages.pot", "rb") as f:
        pot_ids = {m.id for m in read_po(f) if m.id}
    with open("locales/ru/LC_MESSAGES/messages.po", "rb") as f:
        ru_ids = {m.id for m in read_po(f) if m.id}
    assert pot_ids == ru_ids
