"""Group handler: silently delete blocked types, count stats, handle edits."""

from datetime import datetime, timedelta, timezone

from goygram.errors import BadRequestError, ForbiddenError

import texts
from adapters import message_fields
from classify import classify, is_command_exempt
from db import get_blocked, get_notify, get_owner, get_owner_lang, incr_stat, is_whitelisted
from i18n import set_lang
from notices import format_mention, render_unique_notice

NOTIFY_WINDOW = timedelta(minutes=10)
_last_notify: dict[tuple[int], datetime] = {}
# Last bot notice texts per chat (in-memory). A new notice is re-rolled while
# it matches one of these, so back-to-back replies never repeat themselves.
_recent_notice_texts: dict[int, list[str]] = {}
KEEP_NOTICE_TEXTS = 2


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
        await _send_notice(pool, app, chat_id, format_mention(sender), ctype)


async def _send_notice(pool, app, chat_id: int, user: str, ctype: str) -> None:
    """Post a notice whose text doesn't repeat the previous bot replies."""
    previous = _recent_notice_texts.get(chat_id, [])
    text = render_unique_notice(user, ctype, previous)
    try:
        await app.send_msg(chat_id, text)
    except (ForbiddenError, BadRequestError):
        return
    _recent_notice_texts[chat_id] = (previous + [text])[-KEEP_NOTICE_TEXTS:]


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
