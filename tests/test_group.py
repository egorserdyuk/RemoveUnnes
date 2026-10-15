from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from goygram.errors import BadRequestError

import handlers_group
from handlers_group import handle_edited_message, handle_group_message

NOTIFY_WINDOW = handlers_group.NOTIFY_WINDOW


class GMsg:
    """Mimics goygram Obj: normalized attrs + deep .get() into the message dict."""

    def __init__(self, message):
        self._message = message
        self.msg_id = message.get("message_id")
        self.chat_id = (message.get("chat") or {}).get("id")
        self.chat_type = (message.get("chat") or {}).get("type")
        frm = message.get("from")
        self.from_id = frm.get("id") if frm else None
        self.text = message.get("text") or message.get("caption") or ""

    def get(self, key, default=None):
        return self._message.get(key, default)


def make_msg(**kw):
    base = dict(
        message_id=1,
        chat={"id": -1001, "type": "supergroup", "title": "G"},
        text=None,
        entities=[],
    )
    base.update(kw)
    return base


def sender(uid=111, username="bob", first_name="Bob"):
    return {"id": uid, "username": username, "first_name": first_name}


def make_app(self_id=777):
    return SimpleNamespace(
        id=self_id,
        send_msg=AsyncMock(),
        delete_msg=AsyncMock(),
        edit_msg=AsyncMock(),
    )


async def test_blocked_photo_deleted_and_counted():
    msg, app, pool = (
        GMsg(make_msg(**{"from": sender(), "photo": [{}]})),
        make_app(),
        object(),
    )
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.get_notify", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_called_once_with(-1001, 1)
    incr.assert_called_once_with(pool, -1001, "photo")


async def test_allowed_type_passes():
    msg, app, pool = GMsg(make_msg(**{"from": sender(), "text": "hello"})), make_app(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.get_notify", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_not_called()
    incr.assert_not_called()


async def test_private_message_ignored():
    raw = make_msg(**{"from": sender(), "text": "hi"})
    raw["chat"] = {"id": 999, "type": "private"}
    msg, app, pool = GMsg(raw), make_app(), object()
    with patch("handlers_group.get_blocked", AsyncMock()) as gb:
        await handle_group_message(pool, app, msg, 777)
    gb.assert_not_called()
    app.delete_msg.assert_not_called()


async def test_no_rights_dms_owner_once():
    msg = GMsg(make_msg(**{"from": sender(), "photo": [{}]}))
    err = BadRequestError(400, "no rights")
    app = make_app()
    app.delete_msg = AsyncMock(side_effect=err)
    pool = object()
    now = datetime.now(timezone.utc)
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()),
        patch("handlers_group.get_notify", AsyncMock(return_value=False)),
        patch("handlers_group.get_owner", AsyncMock(return_value=111)),
        patch("handlers_group.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_group._last_notify", {}),
        patch("handlers_group._now", return_value=now),
    ):
        await handle_group_message(pool, app, msg, 777)
        await handle_group_message(pool, app, msg, 777)
        assert app.send_msg.call_count == 1
        assert handlers_group._last_notify[(-1001,)] == now


async def test_edited_message_rechecked():
    msg, app, pool = (
        GMsg(make_msg(**{"from": sender(), "photo": [{}]})),
        make_app(),
        object(),
    )
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.get_notify", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_edited_message(pool, app, msg, 777)
    app.delete_msg.assert_called_once()
    incr.assert_called_once()


async def test_notify_sent_when_enabled():
    raw = make_msg(**{"from": sender(), "voice": {"file_id": "v"}})
    msg, app, pool = GMsg(raw), make_app(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"voice"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()),
        patch("handlers_group.get_notify", AsyncMock(return_value=True)),
        patch("handlers_group.get_owner", AsyncMock(return_value=111)),
        patch("handlers_group.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_group.get_notice_ids", AsyncMock(return_value=[])),
        patch("handlers_group.set_notice_ids", AsyncMock()),
    ):
        await handle_group_message(pool, app, msg, 777)
    app.send_msg.assert_called_once()
    args = app.send_msg.call_args[0]
    assert args[0] == -1001
    assert "@bob" in args[1] and "voice message" in args[1]


async def test_notify_silent_when_disabled():
    raw = make_msg(**{"from": sender(), "voice": {"file_id": "v"}})
    msg, app, pool = GMsg(raw), make_app(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"voice"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()),
        patch("handlers_group.get_notify", AsyncMock(return_value=False)),
    ):
        await handle_group_message(pool, app, msg, 777)
    app.send_msg.assert_not_called()


async def test_skips_own_messages():
    msg, app, pool = (
        GMsg(make_msg(**{"from": sender(uid=777), "text": "hi"})),
        make_app(),
        object(),
    )
    with patch("handlers_group.get_blocked", AsyncMock()) as gb:
        await handle_group_message(pool, app, msg, 777)
    gb.assert_not_called()


def _voice_msg():
    return GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v"}}))


def _notify_patches(**over):
    kw = dict(
        get_blocked=AsyncMock(return_value={"voice"}),
        is_whitelisted=AsyncMock(return_value=False),
        incr_stat=AsyncMock(),
        get_notify=AsyncMock(return_value=True),
        get_owner=AsyncMock(return_value=111),
        get_owner_lang=AsyncMock(return_value="en"),
        get_notice_ids=AsyncMock(return_value=[]),
        set_notice_ids=AsyncMock(),
    )
    kw.update(over)
    return kw


async def test_new_notice_deletes_previous_replicas():
    msg, app, pool = _voice_msg(), make_app(), object()
    app.send_msg = AsyncMock(return_value={"message_id": 50})
    patches = _notify_patches(get_notice_ids=AsyncMock(return_value=[30, 40]))
    with (
        patch("handlers_group.get_blocked", patches["get_blocked"]),
        patch("handlers_group.is_whitelisted", patches["is_whitelisted"]),
        patch("handlers_group.incr_stat", patches["incr_stat"]),
        patch("handlers_group.get_notify", patches["get_notify"]),
        patch("handlers_group.get_owner", patches["get_owner"]),
        patch("handlers_group.get_owner_lang", patches["get_owner_lang"]),
        patch("handlers_group.get_notice_ids", patches["get_notice_ids"]),
        patch("handlers_group.set_notice_ids", patches["set_notice_ids"]),
    ):
        await handle_group_message(pool, app, msg, 777)
    assert app.send_msg.await_count == 1
    deleted = sorted(c[0][1] for c in app.delete_msg.call_args_list)
    assert 30 in deleted and 40 in deleted
    patches["set_notice_ids"].assert_called_once_with(pool, -1001, [50])


async def test_notice_cleanup_tolerates_missing_message_id():
    msg, app, pool = _voice_msg(), make_app(), object()
    app.send_msg = AsyncMock(return_value=None)
    patches = _notify_patches(get_notice_ids=AsyncMock(return_value=[30]))
    with (
        patch("handlers_group.get_blocked", patches["get_blocked"]),
        patch("handlers_group.is_whitelisted", patches["is_whitelisted"]),
        patch("handlers_group.incr_stat", patches["incr_stat"]),
        patch("handlers_group.get_notify", patches["get_notify"]),
        patch("handlers_group.get_owner", patches["get_owner"]),
        patch("handlers_group.get_owner_lang", patches["get_owner_lang"]),
        patch("handlers_group.get_notice_ids", patches["get_notice_ids"]),
        patch("handlers_group.set_notice_ids", patches["set_notice_ids"]),
    ):
        await handle_group_message(pool, app, msg, 777)
    assert (-1001, 30) in [c[0] for c in app.delete_msg.call_args_list]
    patches["set_notice_ids"].assert_called_once_with(pool, -1001, [])


async def test_replica_delete_errors_swallowed():
    from goygram.errors import BadRequestError

    msg, app, pool = _voice_msg(), make_app(), object()

    async def fail_replicas(chat_id, msg_id):
        if msg_id != 1:
            raise BadRequestError(400, "gone")
        return None

    app.send_msg = AsyncMock(return_value={"message_id": 50})
    app.delete_msg = AsyncMock(side_effect=fail_replicas)
    patches = _notify_patches(get_notice_ids=AsyncMock(return_value=[30]))
    with (
        patch("handlers_group.get_blocked", patches["get_blocked"]),
        patch("handlers_group.is_whitelisted", patches["is_whitelisted"]),
        patch("handlers_group.incr_stat", patches["incr_stat"]),
        patch("handlers_group.get_notify", patches["get_notify"]),
        patch("handlers_group.get_owner", patches["get_owner"]),
        patch("handlers_group.get_owner_lang", patches["get_owner_lang"]),
        patch("handlers_group.get_notice_ids", patches["get_notice_ids"]),
        patch("handlers_group.set_notice_ids", patches["set_notice_ids"]),
    ):
        await handle_group_message(pool, app, msg, 777)
    patches["set_notice_ids"].assert_called_once_with(pool, -1001, [50])
