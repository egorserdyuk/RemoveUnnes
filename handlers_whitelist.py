"""Whitelist picker flow (private chat only)."""

import itertools

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import texts
from db import add_whitelist, get_owner, get_whitelist, remove_whitelist
from handlers_private import _deny, render_group_menu
from keyboards import picker_kb, remove_reply_kb, whitelist_kb

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


async def _owner_only(pool, chat_id: int, user_id: int) -> bool:
    return await get_owner(pool, chat_id) == user_id

# request_id (per picker message) -> group chat_id. Single polling process.
pending_pick: dict[int, int] = {}
_request_ids = itertools.count(1)


def _next_request_id() -> int:
    return next(_request_ids) % 0x7FFFFFFF or 1


@router.callback_query(F.data.startswith("white:"))
async def on_white_list(cb: CallbackQuery, pool) -> None:
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await cb.message.edit_text(
        "Whitelisted users (bypass all blocks):",
        reply_markup=whitelist_kb(chat_id, await get_whitelist(pool, chat_id)),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("pick_users:"))
async def on_pick_users(cb: CallbackQuery, pool) -> None:
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    request_id = _next_request_id()
    pending_pick[request_id] = chat_id
    await cb.message.answer(
        "Tap the button and pick users (up to 10 at once — repeat to add more):",
        reply_markup=picker_kb(request_id),
    )
    await cb.answer()


@router.message(F.users_shared)
async def on_users_shared(message: Message, pool) -> None:
    shared = message.users_shared
    chat_id = pending_pick.get(shared.request_id)
    if chat_id is None:
        await message.answer("I lost track of which group this was for — tap '+ Add via picker' again.")
        return
    if not await _owner_only(pool, chat_id, message.from_user.id):
        await message.answer(texts.NOT_OWNER)
        return
    rows: list[tuple[int, str | None, str | None]] = []
    for user in shared.users:
        uid = getattr(user, "user_id", None)
        uname = getattr(user, "username", None)
        first = getattr(user, "first_name", None) or ""
        last = getattr(user, "last_name", None) or ""
        display = f"{first} {last}".strip() or None
        rows.append((uid, uname, display))
    await add_whitelist(pool, chat_id, rows)
    pending_pick.pop(shared.request_id, None)
    await message.answer(
        f"Added {len(rows)} user(s) to the whitelist.",
        reply_markup=remove_reply_kb(),
    )


@router.callback_query(F.data.startswith("unwhite:"))
async def on_unwhite(cb: CallbackQuery, pool) -> None:
    _, chat_s, user_s = cb.data.split(":", 2)
    chat_id, user_id = int(chat_s), int(user_s)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await remove_whitelist(pool, chat_id, user_id)
    await cb.message.edit_text(
        "Whitelisted users (bypass all blocks):",
        reply_markup=whitelist_kb(chat_id, await get_whitelist(pool, chat_id)),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("back_group:"))
async def on_back_group(cb: CallbackQuery, pool) -> None:
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    text, kb = await render_group_menu(pool, cb.from_user.id, chat_id)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()
