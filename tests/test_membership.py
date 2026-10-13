from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramForbiddenError


def make_event(old="left", new="member", inviter=111, chat_id=-1001):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id, title="G"),
        from_user=SimpleNamespace(id=inviter),
        old_chat_member=SimpleNamespace(status=old),
        new_chat_member=SimpleNamespace(status=new, user=SimpleNamespace(id=777)),
    )


def make_bot(**kw):
    bot = SimpleNamespace(id=777, send_message=AsyncMock())
    for k, v in kw.items():
        setattr(bot, k, v)
    return bot


def forbidden():
    return TelegramForbiddenError(method=MagicMock(), message="Forbidden: bot was blocked")


async def test_readd_different_owner_fresh_start():
    from handlers_membership import on_my_chat_member

    event = make_event(old="kicked", new="administrator", inviter=222)
    bot, pool = make_bot(), object()
    with patch(
        "handlers_membership.register_group", AsyncMock(return_value="fresh_start")
    ) as rg:
        await on_my_chat_member(event, pool, bot)
    rg.assert_called_once_with(pool, -1001, 222, "G")
    bot.send_message.assert_called_once()


async def test_dm_forbidden_queues_pending():
    from handlers_membership import on_my_chat_member

    event = make_event()
    bot, pool = make_bot(send_message=AsyncMock(side_effect=forbidden())), object()
    with (
        patch("handlers_membership.register_group", AsyncMock(return_value="created")),
        patch("handlers_membership.add_pending_greeting", AsyncMock()) as ap,
    ):
        await on_my_chat_member(event, pool, bot)
    ap.assert_called_once_with(pool, 111, -1001, "G")


async def test_flush_pending_delivers_and_clears():
    from handlers_membership import flush_pending

    bot, pool = make_bot(), object()
    with (
        patch(
            "handlers_membership.list_pending_greetings",
            AsyncMock(return_value=[(-1001, "G")]),
        ),
        patch("handlers_membership.delete_pending_greeting", AsyncMock()) as dp,
    ):
        await flush_pending(pool, bot, 111)
    bot.send_message.assert_called_once()
    dp.assert_called_once_with(pool, 111, -1001)
