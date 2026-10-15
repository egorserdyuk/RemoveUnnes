"""Membership handler: track bot added/removed, greet owner, fresh-start transfer."""

from goygram.errors import ForbiddenError

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

_JOINED = {"member", "administrator"}
_LEFT = {"left", "kicked"}


def _chat_title(member) -> str:
    chat = member.get("chat") or {}
    return chat.get("title") or str(member.chat_id)


async def on_my_chat_member(pool, app, member, bot_id: int) -> None:
    if member.user_id != bot_id:
        return
    old, new = member.old, member.new
    chat_id = member.chat_id
    if old in _LEFT and new in _JOINED:
        owner_id = member.from_id
        title = _chat_title(member)
        await register_group(pool, chat_id, owner_id, title)
        lang = await get_owner_lang(pool, owner_id)
        if lang is None:
            sender = member.get("from") or {}
            lang = detect_language(sender.get("language_code"))
            await set_owner_lang(pool, owner_id, lang)
        set_lang(lang)
        try:
            await app.send_msg(owner_id, texts.CONNECTED(title=title))
        except ForbiddenError:
            await add_pending_greeting(pool, owner_id, chat_id, title)
    elif new in _LEFT:
        await mark_group_inactive(pool, chat_id)


async def flush_pending(pool, app, owner_id: int) -> None:
    """Deliver queued 'Connected' greetings on first /start."""
    set_lang(await get_owner_lang(pool, owner_id) or "en")
    for chat_id, title in await list_pending_greetings(pool, owner_id):
        try:
            await app.send_msg(owner_id, texts.CONNECTED(title=title or str(chat_id)))
        except ForbiddenError:
            continue
        await delete_pending_greeting(pool, owner_id, chat_id)


def register(app, pool, bot_id: int) -> None:
    async def _member(member):
        await on_my_chat_member(pool, app, member, bot_id)

    app.on_member(_member)
