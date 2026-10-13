"""Membership router: track bot added/removed, greet owner, fresh-start transfer."""

from aiogram import Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ChatMemberUpdated

import texts
from db import (
    add_pending_greeting,
    delete_pending_greeting,
    get_owner_lang,
    list_pending_greetings,
    mark_group_inactive,
    register_group,
    set_owner_lang,
)
from i18n import detect_language, set_lang

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
        lang = await get_owner_lang(pool, owner_id)
        if lang is None:
            lang = detect_language(getattr(event.from_user, "language_code", None))
            await set_owner_lang(pool, owner_id, lang)
        set_lang(lang)
        try:
            await bot.send_message(
                owner_id, texts.CONNECTED(title=event.chat.title or str(chat_id))
            )
        except TelegramForbiddenError:
            await add_pending_greeting(
                pool, owner_id, chat_id, event.chat.title or str(chat_id)
            )
    elif new in _LEFT:
        await mark_group_inactive(pool, chat_id)


async def flush_pending(pool, bot, owner_id: int) -> None:
    """Deliver queued 'Connected' greetings on first /start."""
    set_lang(await get_owner_lang(pool, owner_id) or "en")
    for chat_id, title in await list_pending_greetings(pool, owner_id):
        try:
            await bot.send_message(owner_id, texts.CONNECTED(title=title or str(chat_id)))
        except TelegramForbiddenError:
            continue
        await delete_pending_greeting(pool, owner_id, chat_id)
