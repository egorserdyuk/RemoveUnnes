from types import SimpleNamespace

from adapters import is_start_command, message_fields, shared_users


class FakeMsg:
    """Mimics goygram's Obj: normalized attrs + deep .get() into raw update."""

    def __init__(self, message, chat_type="private"):
        self._message = message
        self.msg_id = message.get("message_id")
        self.chat_id = message.get("chat", {}).get("id")
        self.chat_type = chat_type
        sender = message.get("from")
        self.from_id = sender.get("id") if sender else None
        self.text = message.get("text") or message.get("caption") or ""

    def get(self, key, default=None):
        if key in self._message:
            return self._message[key]
        return default


def test_photo_message_fields():
    msg = FakeMsg(
        {
            "message_id": 5,
            "chat": {"id": -1001, "type": "supergroup"},
            "from": {"id": 7, "username": "bob", "first_name": "Bob"},
            "photo": [{"file_id": "p"}],
            "caption": "hi",
        },
        chat_type="supergroup",
    )
    f = message_fields(msg)
    assert f.message_id == 5
    assert f.chat == {"id": -1001, "type": "supergroup"}
    assert (f.from_user.id, f.from_user.username) == (7, "bob")
    assert f.photo == [{"file_id": "p"}]
    assert f.video is None


def test_service_message_fields():
    msg = FakeMsg({"message_id": 6, "chat": {"id": -1001}, "new_chat_members": [{"id": 1}]})
    f = message_fields(msg)
    assert f.new_chat_members == [{"id": 1}]
    assert f.from_user is None


def test_shared_users_parsing():
    msg = FakeMsg(
        {
            "message_id": 9,
            "chat": {"id": 999},
            "users_shared": {
                "request_id": 3,
                "users": [{"user_id": 11, "first_name": "A", "username": "ann"}],
            },
        }
    )
    request_id, rows = shared_users(msg)
    assert request_id == 3
    assert rows == [(11, "ann", "A")]


def test_is_start_command():
    assert is_start_command("/start") is True
    assert is_start_command("/start@mybot extra") is True
    assert is_start_command("/help") is False
    assert is_start_command("hello") is False
    assert is_start_command(None) is False
    assert is_start_command("") is False


def test_fields_feed_classify():
    from classify import classify

    msg = FakeMsg({"message_id": 1, "chat": {"id": 1}, "photo": [{}], "caption": "x"})
    assert classify(message_fields(msg)) == "photo"
    assert classify(message_fields(FakeMsg({"text": "hi"}))) == "text"
