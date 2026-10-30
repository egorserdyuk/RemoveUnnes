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


def make_msg(text="/start", user_id=111, lang="en"):
    return GMsg(
        {
            "message_id": 1,
            "chat": {"id": 999, "type": "private"},
            "from": {"id": user_id, "language_code": lang},
            "text": text,
        }
    )


def make_app():
    return SimpleNamespace(
        send_msg=AsyncMock(), delete_msg=AsyncMock(), edit_msg=AsyncMock()
    )


async def test_start_registers_language_and_lists_groups():
    from handlers_private import on_start

    msg, app, pool = make_msg(), make_app(), object()
    with (
        patch("handlers_membership.flush_pending", AsyncMock()),
        patch("handlers_private.get_owner_lang", AsyncMock(return_value=None)),
        patch("handlers_private.set_owner_lang", AsyncMock()) as sl,
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
    ):
        await on_start(pool, app, msg)
    sl.assert_called_once_with(pool, 111, "en")
    app.send_msg.assert_called_once()
    args, kw = app.send_msg.call_args
    assert args[0] == 999 and "G" not in args[1]
    assert kw["kbd"]["inline_keyboard"][0][0]["callback_data"] == "group:-1001"


async def test_start_detects_russian():
    from handlers_private import on_start

    msg, app, pool = make_msg(lang="ru"), make_app(), object()
    with (
        patch("handlers_membership.flush_pending", AsyncMock()),
        patch("handlers_private.get_owner_lang", AsyncMock(return_value=None)),
        patch("handlers_private.set_owner_lang", AsyncMock()) as sl,
        patch("handlers_private.owner_groups", AsyncMock(return_value=[])),
    ):
        await on_start(pool, app, msg)
    sl.assert_called_once_with(pool, 111, "ru")


async def test_non_owner_tap_changes_nothing():
    from handlers_private import on_group_selected

    cb, app, pool = GCb("group:-1001", 555), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.get_blocked") as gb,
        patch("handlers_private.whitelist_count") as wc,
    ):
        await on_group_selected(pool, app, cb)
    gb.assert_not_called()
    wc.assert_not_called()
    cb.answer.assert_called_once_with(texts.NOT_OWNER(), alert=True)


async def test_toggle_roundtrip_updates_blocked():
    from handlers_private import on_toggle

    cb, app, pool = GCb("toggle:-1001:photo", 111), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.toggle_blocked", AsyncMock(return_value={"photo"})) as tb,
        patch("handlers_private.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
    ):
        await on_toggle(pool, app, cb)
    tb.assert_called_once_with(pool, -1001, "photo")
    assert app.edit_msg.await_count == 1


async def test_notify_toggle_rerenders_menu():
    from handlers_private import on_notify

    cb, app, pool = GCb("notify:-1001", 111), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.toggle_notify", AsyncMock(return_value=True)) as tn,
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
        patch("handlers_private.get_blocked", AsyncMock(return_value=set())),
        patch("handlers_private.whitelist_count", AsyncMock(return_value=0)),
        patch("handlers_private.get_notify", AsyncMock(return_value=True)),
    ):
        await on_notify(pool, app, cb)
    tn.assert_called_once_with(pool, -1001)
    args, kw = app.edit_msg.call_args
    assert args[0] == 999 and "G" in args[2]
    flat = " ".join(b["text"] for row in kw["kbd"]["inline_keyboard"] for b in row)
    assert "Notifications: ON" in flat


async def test_language_switch_stores_and_rerenders():
    from handlers_private import on_language

    cb, app, pool = GCb("lang:ru", 111), make_app(), object()
    with (
        patch("handlers_private.set_owner_lang", AsyncMock()) as sl,
        patch("handlers_private.get_owner_lang", AsyncMock(return_value="ru")),
        patch("handlers_private.owner_groups", AsyncMock(return_value=[])),
    ):
        await on_language(pool, app, cb)
    sl.assert_called_once_with(pool, 111, "ru")
    assert app.edit_msg.await_count == 1


async def test_stats_has_back_button():
    from handlers_private import on_stats

    cb, app, pool = GCb("stats:-1001", 111), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.get_stats", AsyncMock(return_value={})),
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
    ):
        await on_stats(pool, app, cb)
    kb = app.edit_msg.call_args[1]["kbd"]
    datas = [b["callback_data"] for row in kb["inline_keyboard"] for b in row]
    assert "group:-1001" in datas


async def test_private_router_routes_start_and_shared():
    from handlers_private import route_private

    app, pool = make_app(), object()
    with (
        patch("handlers_private.on_start", AsyncMock()) as st,
        patch("handlers_whitelist.on_users_shared", AsyncMock()) as sh,
    ):
        await route_private(pool, app, make_msg("/start"))
        st.assert_called_once()
        sh.assert_not_called()
        st.reset_mock()
        shared = make_msg("")
        shared._message["users_shared"] = {"request_id": 1, "users": []}
        await route_private(pool, app, shared)
        sh.assert_called_once()
        st.assert_not_called()


async def test_private_router_ignores_groups_and_other_text():
    from handlers_private import route_private

    app, pool = make_app(), object()
    grp = make_msg("hello")
    grp.chat_type = "supergroup"
    with (
        patch("handlers_private.on_start", AsyncMock()) as st,
        patch("handlers_whitelist.on_users_shared", AsyncMock()) as sh,
    ):
        await route_private(pool, app, grp)
        await route_private(pool, app, make_msg("just chatting"))
    st.assert_not_called()
    sh.assert_not_called()


async def test_limits_list_renders():
    from handlers_private import on_limits_list

    cb, app, pool = GCb("limits:-1001", 111), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.get_limits", AsyncMock(return_value={"voice": (60, 30)})),
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
    ):
        await on_limits_list(pool, app, cb)
    assert app.edit_msg.await_count == 1


async def test_limit_detail_renders_with_current_values():
    from handlers_private import on_limit_detail

    cb, app, pool = GCb("lim:-1001:voice", 111), make_app(), object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("db.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.get_limit", AsyncMock(return_value=(60, 30))),
    ):
        await on_limit_detail(pool, app, cb)
    assert app.edit_msg.await_count == 1
    args, _kw = app.edit_msg.call_args
    assert "voice" in args[2] and "1m" in args[2] and "30s" in args[2]


async def test_limit_value_parse_error_keeps_pending():
    from handlers_private import _pending_limits, route_private

    _pending_limits.clear()
    _pending_limits[111] = (-1001, "voice", "dur")
    app, pool = make_app(), object()
    with patch("handlers_private.set_limit", AsyncMock()) as sl:
        await route_private(pool, app, make_msg("5x"))
    sl.assert_not_called()
    assert _pending_limits.get(111) == (-1001, "voice", "dur")
    app.send_msg.assert_called_once()
    assert "30s" in app.send_msg.call_args[0][1]


async def test_limit_value_success_clears_pending():
    from handlers_private import _pending_limits, route_private

    _pending_limits.clear()
    _pending_limits[111] = (-1001, "voice", "dur")
    app, pool = make_app(), object()
    with (
        patch("handlers_private.get_limit", AsyncMock(return_value=(None, 30))),
        patch("handlers_private.set_limit", AsyncMock()) as sl,
    ):
        await route_private(pool, app, make_msg("1m"))
    sl.assert_called_once_with(pool, -1001, "voice", 60, 30)
    assert 111 not in _pending_limits
    app.send_msg.assert_called_once()


async def test_start_clears_pending():
    from handlers_private import _pending_limits, route_private

    _pending_limits.clear()
    _pending_limits[111] = (-1001, "voice", "dur")
    app, pool = make_app(), object()
    with (
        patch("handlers_private.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_private.owner_groups", AsyncMock(return_value=[])),
        patch("handlers_membership.flush_pending", AsyncMock()),
    ):
        await route_private(pool, app, make_msg("/start"))
    assert 111 not in _pending_limits
