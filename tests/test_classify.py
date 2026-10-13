from types import SimpleNamespace

from classify import CONTENT_TYPES, classify, is_command_exempt


def photo_msg(**kw):
    base = dict(
        story=None, photo=None, video=None, video_note=None,
        voice=None, audio=None, document=None, animation=None, sticker=None,
        poll=None, contact=None, location=None, venue=None, dice=None,
        game=None, invoice=None, successful_payment=None, checklist=None,
        text=None, caption=None, entities=None,
        new_chat_members=None, left_chat_member=None, pinned_message=None,
        chat_shared=None, users_shared=None, new_chat_title=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_priority_order_text_last():
    assert CONTENT_TYPES[-1] == "text"
    assert "photo" in CONTENT_TYPES and "video_note" in CONTENT_TYPES


def test_captioned_photo_counts_as_photo():
    assert classify(photo_msg(photo=[{"file_id": "p"}], caption="hi")) == "photo"


def test_plain_text_classifies():
    assert classify(photo_msg(text="hello")) == "text"


def test_command_exempt_when_text_blocked():
    m = photo_msg(
        text="/start@otherbot",
        entities=[SimpleNamespace(type="bot_command", offset=0, length=6)],
    )
    assert is_command_exempt(m) is True
    assert classify(m) == "text"


def test_non_command_text_not_exempt():
    assert is_command_exempt(photo_msg(text="hello")) is False


def test_service_message_returns_none():
    assert classify(photo_msg(new_chat_members=[{"id": 1}])) is None


def test_anonymous_channel_photo_classifies():
    assert classify(photo_msg(photo=[{"file_id": "p"}])) == "photo"
