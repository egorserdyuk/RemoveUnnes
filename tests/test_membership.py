from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from goygram.errors import ForbiddenError


class GMember:
    def __init__(self, old="left", new="member", inviter=111, chat_id=-1001, user_id=777):
        self.old = old
        self.new = new
        self.chat_id = chat_id
        self.user_id = user_id
        self.from_id = inviter
        self._chat = {"id": chat_id, "title": "G"}

    def get(self, key, default=None):
        if key == "chat":
            return self._chat
        return default


def make_app(**kw):
    app = SimpleNamespace(
        send_msg=AsyncMock(), delete_msg=AsyncMock(), edit_msg=AsyncMock()
    )
    for k, v in kw.items():
        setattr(app, k, v)
    return app


async def test_readd_different_owner_fresh_start():
    from handlers_membership import on_my_chat_member

    member = GMember(old="kicked", new="administrator", inviter=222)
    app, pool = make_app(), object()
    with (
        patch("handlers_membership.register_group", AsyncMock(return_value="fresh_start")) as rg,
        patch("handlers_membership.get_owner_lang", AsyncMock(return_value=None)),
        patch("handlers_membership.set_owner_lang", AsyncMock()),
    ):
        await on_my_chat_member(pool, app, member, 777)
    rg.assert_called_once_with(pool, -1001, 222, "G")
    app.send_msg.assert_called_once()


async def test_ignores_other_members():
    from handlers_membership import on_my_chat_member

    member = GMember(user_id=555)
    app, pool = make_app(), object()
    with patch("handlers_membership.register_group", AsyncMock()) as rg:
        await on_my_chat_member(pool, app, member, 777)
    rg.assert_not_called()
    app.send_msg.assert_not_called()


async def test_dm_forbidden_queues_pending():
    from handlers_membership import on_my_chat_member

    member = GMember()
    app = make_app(send_msg=AsyncMock(side_effect=ForbiddenError(403, "blocked")))
    pool = object()
    with (
        patch("handlers_membership.register_group", AsyncMock(return_value="created")),
        patch("handlers_membership.get_owner_lang", AsyncMock(return_value=None)),
        patch("handlers_membership.set_owner_lang", AsyncMock()),
        patch("handlers_membership.add_pending_greeting", AsyncMock()) as ap,
    ):
        await on_my_chat_member(pool, app, member, 777)
    ap.assert_called_once_with(pool, 111, -1001, "G")


async def test_left_marks_inactive():
    from handlers_membership import on_my_chat_member

    member = GMember(old="member", new="left")
    app, pool = make_app(), object()
    with patch("handlers_membership.mark_group_inactive", AsyncMock()) as mi:
        await on_my_chat_member(pool, app, member, 777)
    mi.assert_called_once_with(pool, -1001)


async def test_flush_pending_delivers_and_clears():
    from handlers_membership import flush_pending

    app, pool = make_app(), object()
    with (
        patch(
            "handlers_membership.list_pending_greetings",
            AsyncMock(return_value=[(-1001, "G")]),
        ),
        patch("handlers_membership.get_owner_lang", AsyncMock(return_value="en")),
        patch("handlers_membership.delete_pending_greeting", AsyncMock()) as dp,
    ):
        await flush_pending(pool, app, 111)
    app.send_msg.assert_called_once()
    dp.assert_called_once_with(pool, 111, -1001)
