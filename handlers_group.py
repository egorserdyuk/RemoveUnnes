"""Group router: silently delete blocked types, count stats, handle edits."""

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import Message

import texts
from classify import classify, is_command_exempt
from db import get_blocked, get_notify, get_owner, incr_stat, is_whitelisted
from notices import format_mention, render_notice

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.edited_message.filter(F.chat.type.in_({"group", "supergroup"}))

NOTIFY_WINDOW = timedelta(minutes=10)
_last_notify: dict[tuple[int], datetime] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _notify_no_rights(pool, bot, chat_id: int, title: str) -> None:
    key = (chat_id,)
    now = _now()
    last = _last_notify.get(key)
    if last is not None and now - last < NOTIFY_WINDOW:
        return
    _last_notify[key] = now
    owner = await get_owner(pool, chat_id)
    if owner is None:
        return
    try:
        await bot.send_message(owner, texts.NEED_ADMIN.format(title=title))
    except TelegramAPIError:
        pass


async def _handle(message: Message, pool, bot) -> None:
    sender = message.from_user
    if sender is not None and sender.id == bot.id:
        return
    ctype = classify(message)
    if ctype is None or is_command_exempt(message):
        return
    chat_id = message.chat.id
    sender_id = sender.id if sender is not None else None
    if sender_id is not None and await is_whitelisted(pool, chat_id, sender_id):
        return
    if ctype not in await get_blocked(pool, chat_id):
        return
    try:
        await bot.delete_message(chat_id, message.message_id)
    except TelegramBadRequest:
        await _notify_no_rights(
            pool, bot, chat_id, getattr(message.chat, "title", None) or str(chat_id)
        )
        return
    await incr_stat(pool, chat_id, ctype)
    if await get_notify(pool, chat_id):
        try:
            await bot.send_message(chat_id, render_notice(format_mention(sender), ctype))
        except TelegramAPIError:
            pass


@router.message()
async def handle_group_message(message: Message, pool, bot) -> None:
    await _handle(message, pool, bot)


@router.edited_message()
async def handle_edited_message(message: Message, pool, bot) -> None:
    await _handle(message, pool, bot)
