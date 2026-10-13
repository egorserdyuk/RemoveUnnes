from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

NOTIFY_WINDOW = timedelta(minutes=10)


def make_msg(*, text=None, entities=None, photo=None, from_id=111, msg_id=1, chat_id=-1001):
    return SimpleNamespace(
        message_id=msg_id,
        chat=SimpleNamespace(id=chat_id, type="supergroup", title="G"),
        from_user=SimpleNamespace(id=from_id) if from_id is not None else None,
        sender_chat=None,
        text=text,
        entities=entities,
        photo=photo,
        video=None, video_note=None, voice=None, audio=None, document=None,
        animation=None, sticker=None, poll=None, contact=None, location=None,
        venue=None, dice=None, game=None, invoice=None, successful_payment=None,
        checklist=None, story=None,
        new_chat_members=None, left_chat_member=None, pinned_message=None,
        chat_shared=None, users_shared=None,
    )


def make_bot(self_id=777):
    return SimpleNamespace(id=self_id, delete_message=AsyncMock(), send_message=AsyncMock())


async def test_blocked_photo_deleted_and_counted():
    from handlers_group import handle_group_message

    msg, bot, pool = make_msg(photo=[{"file_id": "p"}]), make_bot(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_group_message(msg, pool, bot)
    bot.delete_message.assert_called_once_with(-1001, 1)
    incr.assert_called_once_with(pool, -1001, "photo")


async def test_allowed_type_passes():
    from handlers_group import handle_group_message

    msg, bot, pool = make_msg(text="hello"), make_bot(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_group_message(msg, pool, bot)
    bot.delete_message.assert_not_called()
    incr.assert_not_called()


async def test_no_rights_dms_owner_once():
    from unittest.mock import MagicMock

    from aiogram.exceptions import TelegramBadRequest

    import handlers_group
    from handlers_group import handle_group_message

    msg = make_msg(photo=[{"file_id": "p"}])
    err = TelegramBadRequest(method=MagicMock(), message="no rights")
    bot = make_bot()
    bot.delete_message = AsyncMock(side_effect=err)
    pool = object()
    now = datetime.now(timezone.utc)
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()),
        patch("handlers_group.get_owner", AsyncMock(return_value=111)),
        patch("handlers_group._last_notify", {}),
        patch("handlers_group._now", return_value=now),
    ):
        await handle_group_message(msg, pool, bot)
        await handle_group_message(msg, pool, bot)
        assert bot.send_message.call_count == 1
        assert handlers_group._last_notify[(-1001,)] == now


async def test_edited_message_rechecked():
    from handlers_group import handle_edited_message

    msg, bot, pool = make_msg(photo=[{"file_id": "p"}]), make_bot(), object()
    with (
        patch("handlers_group.get_blocked", AsyncMock(return_value={"photo"})),
        patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)),
        patch("handlers_group.incr_stat", AsyncMock()) as incr,
    ):
        await handle_edited_message(msg, pool, bot)
    bot.delete_message.assert_called_once()
    incr.assert_called_once()
