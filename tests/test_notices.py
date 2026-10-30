from notices import CONTENT_LABELS, INSULTS, NOTICE_TEMPLATES, format_mention, render_notice
from types import SimpleNamespace


def first(choices):
    return choices[0]


def test_all_templates_render_with_user_and_type():
    from notices import NOTICE_TEMPLATES_COOLDOWN, NOTICE_TEMPLATES_DURATION

    for tpl in NOTICE_TEMPLATES:
        assert "{user}" in tpl and "{type}" in tpl
        text = tpl.format(user="@bob", insult="rascal", type="voice message")
        assert "@bob" in text and "voice message" in text
    for pool in list(NOTICE_TEMPLATES_DURATION.values()) + list(
        NOTICE_TEMPLATES_COOLDOWN.values()
    ):
        for tpl in pool:
            assert "{user}" in tpl
            text = tpl.format(user="@bob", insult="rascal", type="voice message")
            assert "@bob" in text


def test_all_ru_replies_render_with_user():
    from notices import (
        RUSSIAN_REPLIES,
        RUSSIAN_REPLIES_BLOCKED,
        RUSSIAN_REPLIES_COOLDOWN,
        RUSSIAN_REPLIES_DURATION,
    )

    pools = (
        [RUSSIAN_REPLIES]
        + list(RUSSIAN_REPLIES_BLOCKED.values())
        + list(RUSSIAN_REPLIES_DURATION.values())
        + list(RUSSIAN_REPLIES_COOLDOWN.values())
    )
    for pool in pools:
        for tpl in pool:
            assert "{user}" in tpl
            assert "@bob" in tpl.format(user="@bob")


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


class ScriptedRng:
    """Returns pre-scripted template/insult picks in call order."""

    def __init__(self, picks):
        self.picks = list(picks)

    def __call__(self, choices):
        pick = self.picks.pop(0)
        assert pick in choices, f"{pick!r} not a valid choice"
        return pick


def test_unique_notice_rerolls_duplicates():
    from notices import NOTICE_TEMPLATES, render_unique_notice

    dupe = NOTICE_TEMPLATES[0].format(user="@bob", insult="rascal", type="voice message")
    other = NOTICE_TEMPLATES[1].format(user="@bob", insult="rascal", type="voice message")
    rng = ScriptedRng([NOTICE_TEMPLATES[0], "rascal", NOTICE_TEMPLATES[1], "rascal"])
    assert render_unique_notice("@bob", "voice", [dupe], rng=rng) == other


def test_unique_notice_passes_through_when_fresh():
    from notices import NOTICE_TEMPLATES, render_unique_notice

    rng = ScriptedRng([NOTICE_TEMPLATES[0], "jerk"])
    text = render_unique_notice("@bob", "voice", ["something else"], rng=rng)
    assert "@bob" in text and "voice message" in text


def test_unique_notice_gives_up_after_max_attempts():
    import notices
    from notices import render_unique_notice

    rng = ScriptedRng(
        [notices.NOTICE_TEMPLATES[0], "jerk"] * (notices.MAX_UNIQUE_ATTEMPTS + 1)
    )
    dupe = notices.NOTICE_TEMPLATES[0].format(
        user="@bob", insult="jerk", type="voice message"
    )
    assert render_unique_notice("@bob", "voice", [dupe], rng=rng) == dupe


def test_render_notice_selects_scenario_pool(monkeypatch):
    import notices

    tpl = "Slow down, {user} — one {type} at a time."
    monkeypatch.setattr(notices, "NOTICE_TEMPLATES_COOLDOWN", {"text": [tpl]})
    text = render_notice("@bob", "text", reason="cooldown", rng=first)
    assert text == tpl.format(user="@bob", type="text message")
    generic = render_notice("@bob", "text", rng=first)
    assert generic != text
    assert render_notice("@bob", "photo", reason="cooldown", rng=first) == render_notice(
        "@bob", "photo", rng=first
    )


def test_render_notice_falls_back_to_generic_pool(monkeypatch):
    import notices

    monkeypatch.setattr(notices, "NOTICE_TEMPLATES_DURATION", {})
    monkeypatch.setattr(notices, "NOTICE_TEMPLATES_COOLDOWN", {})
    generic = render_notice("@bob", "voice", rng=first)
    assert render_notice("@bob", "voice", reason="duration", rng=first) == generic
    assert render_notice("@bob", "voice", reason="cooldown", rng=first) == generic


def test_render_notice_ru_selects_scenario_pool(monkeypatch):
    import notices
    from i18n import set_lang

    monkeypatch.setattr(
        notices, "RUSSIAN_REPLIES_COOLDOWN", {"text": ["{user}, помедленнее!"]}
    )
    set_lang("ru")
    try:
        assert render_notice("@bob", "text", reason="cooldown", rng=first) == "@bob, помедленнее!"
        assert render_notice("@bob", "text", rng=first) != "@bob, помедленнее!"
        assert render_notice("@bob", "photo", reason="cooldown", rng=first) == render_notice(
            "@bob", "photo", rng=first
        )
    finally:
        set_lang("en")


def test_blocked_voice_ru_uses_voice_pool():
    import notices
    from i18n import set_lang

    set_lang("ru")
    try:
        text = render_notice("@bob", "voice", reason="blocked", rng=first)
        assert text == notices.RUSSIAN_REPLIES_BLOCKED["voice"][0].format(user="@bob")
        assert "голосовое" in text or "Голосовое" in text or "рот" in text or "слуша" in text
    finally:
        set_lang("en")


def test_blocked_other_type_ru_uses_generic_pool():
    import notices
    from i18n import set_lang

    set_lang("ru")
    try:
        text = render_notice("@bob", "photo", reason="blocked", rng=first)
        assert text == notices.RUSSIAN_REPLIES[0].format(user="@bob")
    finally:
        set_lang("en")
