"""Private-chat router: /start, group list, per-group config, stats."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import texts
from db import (
    format_stats,
    get_blocked,
    get_owner,
    get_stats,
    owner_groups,
    reset_group_data,
    reset_stats,
    toggle_blocked,
    whitelist_count,
)
from keyboards import group_menu_kb, groups_kb, types_kb

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


async def _owner_only(pool, chat_id: int, user_id: int) -> bool:
    return await get_owner(pool, chat_id) == user_id


async def _deny(cb: CallbackQuery) -> None:
    await cb.answer(texts.NOT_OWNER, show_alert=True)


async def _group_title(pool, owner_id: int, chat_id: int) -> str:
    for cid, title in await owner_groups(pool, owner_id):
        if cid == chat_id:
            return title or str(chat_id)
    return str(chat_id)


def _parse_chat(data: str) -> int:
    return int(data.split(":", 1)[1])


@router.message(Command("start"))
async def on_start(message: Message, pool) -> None:
    owner_id = message.from_user.id
    try:
        from handlers_membership import flush_pending

        await flush_pending(pool, message.bot, owner_id)
    except ImportError:
        pass
    groups = await owner_groups(pool, owner_id)
    if groups:
        await message.answer(texts.START + "\n\n" + texts.MY_GROUPS, reply_markup=groups_kb(groups))
    else:
        await message.answer(texts.START + "\n\n" + texts.GROUPS_EMPTY)


@router.callback_query(F.data == "back_groups")
async def on_back_groups(cb: CallbackQuery, pool) -> None:
    groups = await owner_groups(pool, cb.from_user.id)
    text = texts.MY_GROUPS if groups else texts.GROUPS_EMPTY
    await cb.message.edit_text(text, reply_markup=groups_kb(groups) if groups else None)
    await cb.answer()


@router.callback_query(F.data.startswith("group:"))
async def on_group_selected(cb: CallbackQuery, pool) -> None:
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    title = await _group_title(pool, cb.from_user.id, chat_id)
    await cb.message.edit_text(
        texts.GROUP_TITLE.format(title=title),
        reply_markup=group_menu_kb(
            chat_id,
            n_blocked=len(await get_blocked(pool, chat_id)),
            n_white=await whitelist_count(pool, chat_id),
        ),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("types:"))
async def on_types_list(cb: CallbackQuery, pool) -> None:
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await cb.message.edit_text(
        f"Blocked types for {await _group_title(pool, cb.from_user.id, chat_id)}"
        f" (tap to toggle):\n{texts.COMMANDS_EXEMPT_NOTE}",
        reply_markup=types_kb(chat_id, await get_blocked(pool, chat_id)),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def on_toggle(cb: CallbackQuery, pool) -> None:
    _, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    blocked = await toggle_blocked(pool, chat_id, ctype)
    await cb.message.edit_text(
        f"Blocked types for {await _group_title(pool, cb.from_user.id, chat_id)}"
        f" (tap to toggle):\n{texts.COMMANDS_EXEMPT_NOTE}",
        reply_markup=types_kb(chat_id, blocked),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("stats:"))
async def on_stats(cb: CallbackQuery, pool) -> None:
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    stats = await get_stats(pool, chat_id)
    body = format_stats(stats)
    if body == "nothing removed yet":
        body = texts.STATS_EMPTY.format(title=await _group_title(pool, cb.from_user.id, chat_id))
    else:
        body = f"{await _group_title(pool, cb.from_user.id, chat_id)}: {body}"
    await cb.message.edit_text(body)
    await cb.answer()


@router.callback_query(F.data.startswith("reset_stats:"))
async def on_reset_stats(cb: CallbackQuery, pool) -> None:
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await reset_stats(pool, chat_id)
    await cb.message.edit_text("Stats cleared.")
    await cb.answer()


@router.callback_query(F.data.startswith("reset_group:"))
async def on_reset_group(cb: CallbackQuery, pool) -> None:
    parts = cb.data.split(":")
    chat_id = int(parts[1])
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    if len(parts) == 3 and parts[2] == "confirm":
        await reset_group_data(pool, chat_id)
        await cb.message.edit_text("Group data cleared. Everything is allowed again.")
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="Yes, clear it", callback_data=f"reset_group:{chat_id}:confirm")
        builder.button(text="Cancel", callback_data=f"group:{chat_id}")
        builder.adjust(1)
        await cb.message.edit_text(
            "Clear blocked types, whitelist and stats for this group?",
            reply_markup=builder.as_markup(),
        )
    await cb.answer()


async def render_group_menu(pool, owner_id: int, chat_id: int):
    """Shared group-menu render used by the whitelist router's Back button."""
    title = await _group_title(pool, owner_id, chat_id)
    return (
        texts.GROUP_TITLE.format(title=title),
        group_menu_kb(
            chat_id,
            n_blocked=len(await get_blocked(pool, chat_id)),
            n_white=await whitelist_count(pool, chat_id),
        ),
    )
