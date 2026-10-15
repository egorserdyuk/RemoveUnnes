"""Whitelist picker flow (private chat only)."""

import itertools
from types import SimpleNamespace

import texts
from adapters import shared_users
from db import add_whitelist, get_owner, get_whitelist, remove_whitelist
from handlers_private import _deny, render_group_menu
from i18n import _, activate_owner_lang, n
from keyboards import picker_kb, remove_reply_kb, whitelist_kb

# request_id (per picker message) -> group chat_id. Single polling process.
pending_pick: dict[int, int] = {}
_request_ids = itertools.count(1)


def _next_request_id() -> int:
    return next(_request_ids) % 0x7FFFFFFF or 1


def _tg_user(msg) -> SimpleNamespace:
    return SimpleNamespace(id=msg.from_id, language_code=getattr(msg, "language_code", None))


async def _owner_only(pool, chat_id: int, user_id: int) -> bool:
    return await get_owner(pool, chat_id) == user_id


async def on_white_list(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await app.edit_msg(
        cb.chat_id,
        cb.msg_id,
        _("Whitelisted users (bypass all blocks):"),
        kbd=whitelist_kb(chat_id, await get_whitelist(pool, chat_id)),
    )
    await cb.answer()


async def on_pick_users(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    request_id = _next_request_id()
    pending_pick[request_id] = chat_id
    await app.send_msg(
        cb.from_id,
        _("Tap the button and pick users (up to 10 at once — repeat to add more):"),
        kbd=picker_kb(request_id),
    )
    await cb.answer()


async def on_users_shared(pool, app, msg) -> None:
    await activate_owner_lang(pool, _tg_user(msg))
    request_id, rows = shared_users(msg)
    chat_id = pending_pick.get(request_id)
    if chat_id is None:
        await app.send_msg(
            msg.chat_id,
            _("I lost track of which group this was for — tap '+ Add via picker' again."),
        )
        return
    if not await _owner_only(pool, chat_id, msg.from_id):
        await app.send_msg(msg.chat_id, texts.NOT_OWNER())
        return
    await add_whitelist(pool, chat_id, rows)
    pending_pick.pop(request_id, None)
    await app.send_msg(
        msg.chat_id,
        n(
            "Added {n} user to the whitelist.",
            "Added {n} users to the whitelist.",
            len(rows),
        ).format(n=len(rows)),
        kbd=remove_reply_kb(),
    )


async def on_unwhite(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, user_s = cb.data.split(":", 2)
    chat_id, user_id = int(chat_s), int(user_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await remove_whitelist(pool, chat_id, user_id)
    await app.edit_msg(
        cb.chat_id,
        cb.msg_id,
        _("Whitelisted users (bypass all blocks):"),
        kbd=whitelist_kb(chat_id, await get_whitelist(pool, chat_id)),
    )
    await cb.answer()


async def on_back_group(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    text, kb = await render_group_menu(pool, cb.from_id, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()
