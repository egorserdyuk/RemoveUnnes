"""Group handler: silently delete blocked types, count stats, handle edits."""

from datetime import datetime, timedelta, timezone

from goygram.errors import BadRequestError, ForbiddenError

import texts
from adapters import message_fields
from classify import classify, is_command_exempt
from db import (
    get_blocked,
    get_notice_ids,
    get_notify,
    get_owner,
    get_owner_lang,
    incr_stat,
    is_whitelisted,
    set_notice_ids,
)
from i18n import set_lang
from notices import format_mention, render_notice

NOTIFY_WINDOW = timedelta(minutes=10)
_last_notify: dict[tuple[int], datetime] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _notify_no_rights(pool, app, chat_id: int, title: str) -> None:
    key = (chat_id,)
    now = _now()
    last = _last_notify.get(key)
    if last is not None and now - last < NOTIFY_WINDOW:
        return
    _last_notify[key] = now
    owner = await get_owner(pool, chat_id)
    if owner is None:
        return
    set_lang(await get_owner_lang(pool, owner) or "en")
    try:
        await app.send_msg(owner, texts.NEED_ADMIN(title=title))
    except (ForbiddenError, BadRequestError):
        pass


async def _handle(pool, app, msg, bot_id: int) -> None:
    if msg.chat_type not in ("group", "supergroup"):
        return
    fields = message_fields(msg)
    sender = fields.from_user
    if sender is not None and sender.id == bot_id:
        return
    ctype = classify(fields)
    if ctype is None or is_command_exempt(fields):
        return
    chat_id = msg.chat_id
    sender_id = sender.id if sender is not None else None
    if sender_id is not None and await is_whitelisted(pool, chat_id, sender_id):
        return
    if ctype not in await get_blocked(pool, chat_id):
        return
    try:
        await app.delete_msg(chat_id, msg.msg_id)
    except BadRequestError:
        await _notify_no_rights(pool, app, chat_id, fields.chat_title or str(chat_id))
        return
    await incr_stat(pool, chat_id, ctype)
    if await get_notify(pool, chat_id):
        owner = await get_owner(pool, chat_id)
        lang = await get_owner_lang(pool, owner) if owner is not None else None
        set_lang(lang or "en")
        await _send_notice(pool, app, chat_id, render_notice(format_mention(sender), ctype))


async def _send_notice(pool, app, chat_id: int, text: str) -> None:
    """Post a notice, deleting all previous notice replicas first (keep latest)."""
    try:
        sent = await app.send_msg(chat_id, text)
    except (ForbiddenError, BadRequestError):
        return
    new_id = sent.get("message_id") if isinstance(sent, dict) else None
    old_ids = await get_notice_ids(pool, chat_id)
    for mid in old_ids:
        if mid != new_id:
            try:
                await app.delete_msg(chat_id, mid)
            except (ForbiddenError, BadRequestError):
                pass
    await set_notice_ids(pool, chat_id, [new_id] if new_id is not None else [])


async def handle_group_message(pool, app, msg, bot_id: int) -> None:
    await _handle(pool, app, msg, bot_id)


async def handle_edited_message(pool, app, msg, bot_id: int) -> None:
    await _handle(pool, app, msg, bot_id)


def register(app, pool, bot_id: int) -> None:
    async def _msg(msg):
        await handle_group_message(pool, app, msg, bot_id)

    async def _edit(msg):
        await handle_edited_message(pool, app, msg, bot_id)

    app.on_msg(_msg)
    app.on_edit(_edit)
