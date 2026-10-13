from notices import CONTENT_LABELS, INSULTS, NOTICE_TEMPLATES, format_mention, render_notice
from types import SimpleNamespace


def first(choices):
    return choices[0]


def test_all_templates_render_with_user_and_type():
    for tpl in NOTICE_TEMPLATES:
        assert "{user}" in tpl and "{type}" in tpl
        text = tpl.format(user="@bob", insult="rascal", type="voice message")
        assert "@bob" in text and "voice message" in text


def test_render_notice_contains_user_type_and_known_insult():
    text = render_notice("@bob", "voice", rng=first)
    assert "@bob" in text
    assert "voice message" in text
    assert any(insult in text for insult in INSULTS)


def test_every_content_type_has_a_label():
    from classify import CONTENT_TYPES

    assert set(CONTENT_LABELS) == set(CONTENT_TYPES)


def test_format_mention_prefers_username():
    m = SimpleNamespace(username="bob", first_name="Bob")
    assert format_mention(m) == "@bob"


def test_format_mention_falls_back_to_name_then_someone():
    assert format_mention(SimpleNamespace(username=None, first_name="Bob")) == "Bob"
    assert format_mention(None) == "someone"
