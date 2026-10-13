"""Membership router: track bot added/removed, greet owner, fresh-start transfer."""

from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ChatMemberUpdated

import texts
from db import (
    add_pending_greeting,
    delete_pending_greeting,
    list_pending_greetings,
    mark_group_inactive,
    register_group,
)

router = Router()

_JOINED = {"member", "administrator"}
_LEFT = {"left", "kicked"}


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, pool, bot) -> None:
    if event.new_chat_member.user.id != bot.id:
        return
    old, new = event.old_chat_member.status, event.new_chat_member.status
    chat_id = event.chat.id
    if old in _LEFT and new in _JOINED:
        owner_id = event.from_user.id
        await register_group(pool, chat_id, owner_id, event.chat.title or str(chat_id))
        try:
            await bot.send_message(
                owner_id, texts.CONNECTED.format(title=event.chat.title or str(chat_id))
            )
        except TelegramForbiddenError:
            await add_pending_greeting(
                pool, owner_id, chat_id, event.chat.title or str(chat_id)
            )
    elif new in _LEFT:
        await mark_group_inactive(pool, chat_id)


async def flush_pending(pool, bot, owner_id: int) -> None:
    """Deliver queued 'Connected' greetings on first /start."""
    for chat_id, title in await list_pending_greetings(pool, owner_id):
        try:
            await bot.send_message(owner_id, texts.CONNECTED.format(title=title or str(chat_id)))
        except TelegramForbiddenError:
            continue
        await delete_pending_greeting(pool, owner_id, chat_id)
