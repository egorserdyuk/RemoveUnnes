from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import texts


class GMsg:
    def __init__(self, message):
        self._message = message
        self.msg_id = message.get("message_id")
        self.chat_id = (message.get("chat") or {}).get("id")
        self.chat_type = (message.get("chat") or {}).get("type")
        frm = message.get("from")
        self.from_id = frm.get("id") if frm else None
        self.text = message.get("text") or ""

    def get(self, key, default=None):
        return self._message.get(key, default)


class GCb:
    def __init__(self, data, user_id, chat_id=999, msg_id=10):
        self.data = data
        self.from_id = user_id
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.answer = AsyncMock()


def make_app():
    return SimpleNamespace(
        send_msg=AsyncMock(), delete_msg=AsyncMock(), edit_msg=AsyncMock()
    )


def make_shared(user_ids, owner_id=111):
    users = [
        {"user_id": u, "first_name": None, "last_name": None, "username": None}
        for u in user_ids
    ]
    return GMsg(
        {
            "message_id": 3,
            "chat": {"id": 999, "type": "private"},
            "from": {"id": owner_id},
            "users_shared": {"request_id": 7, "users": users},
        }
    )


async def test_users_shared_adds_all_ids():
    from handlers_whitelist import on_users_shared, pending_pick

    msg, app, pool = make_shared([11, 22, 33]), make_app(), object()
    pending_pick[7] = -1001
    try:
        with (
            patch("handlers_whitelist.get_owner", AsyncMock(return_value=111)),
            patch("db.get_owner_lang", AsyncMock(return_value="en")),
            patch("handlers_whitelist.add_whitelist", AsyncMock()) as aw,
        ):
            await on_users_shared(pool, app, msg)
    finally:
        pending_pick.pop(7, None)
    rows = aw.call_args[0][2]
    assert sorted(u for u, _, _ in rows) == [11, 22, 33]
    assert 7 not in pending_pick


async def test_users_shared_unknown_request_id_asks_to_retry():
    from handlers_whitelist import on_users_shared

    msg, app, pool = make_shared([11]), make_app(), object()
    with (
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_whitelist.add_whitelist", AsyncMock()) as aw,
    ):
        await on_users_shared(pool, app, msg)
    aw.assert_not_called()
    app.send_msg.assert_called_once()


async def test_unwhite_requires_owner():
    from handlers_whitelist import on_unwhite

    cb, app, pool = GCb("unwhite:-1001:11", 555), make_app(), object()
    with (
        patch("handlers_whitelist.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_whitelist.remove_whitelist") as rw,
    ):
        await on_unwhite(pool, app, cb)
    rw.assert_not_called()
    cb.answer.assert_called_once_with(texts.NOT_OWNER(), alert=True)


async def test_white_list_renders_removes():
    from handlers_whitelist import on_white_list

    cb, app, pool = GCb("white:-1001", 111), make_app(), object()
    with (
        patch("handlers_whitelist.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_whitelist.get_whitelist", AsyncMock(return_value=[(7, "bob")])),
    ):
        await on_white_list(pool, app, cb)
    kb = app.edit_msg.call_args[1]["kbd"]
    datas = [b["callback_data"] for row in kb["inline_keyboard"] for b in row]
    assert "unwhite:-1001:7" in datas
