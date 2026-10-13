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

    def keys(path):
        with open(path, "rb") as f:
            out = set()
            for m in read_po(f):
                if not m.id:
                    continue
                out.add(m.id if isinstance(m.id, str) else m.id[0])
                if m.pluralizable:
                    out.add(m.id[1])
            return out

    assert keys("locales/messages.pot") == keys("locales/ru/LC_MESSAGES/messages.po")


def test_notices_and_stat_forms_are_extractable():
    # Strings passed to _()/n() via variables are invisible to pybabel unless
    # marked with msgid()/msgid_plural() — this guards the whole dynamic set.
    from babel.messages.pofile import read_po

    with open("locales/messages.pot", "rb") as f:
        pot_keys = set()
        for m in read_po(f):
            if not m.id:
                continue
            pot_keys.add(m.id if isinstance(m.id, str) else m.id[0])
            if m.pluralizable:
                pot_keys.add(m.id[1])

    import notices
    from db import STAT_FORMS

    want = (
        set(notices.INSULTS)
        | set(notices.NOTICE_TEMPLATES)
        | set(notices.CONTENT_LABELS.values())
        | {"someone"}
        | {s for pair in STAT_FORMS.values() for s in pair}
    )
    assert want - pot_keys == set()
