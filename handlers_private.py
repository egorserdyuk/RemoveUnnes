"""Private-chat router: /start, group list, per-group config, stats, language."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import texts
from db import (
    format_stats,
    get_blocked,
    get_notify,
    get_owner,
    get_owner_lang,
    get_stats,
    owner_groups,
    reset_group_data,
    reset_stats,
    set_owner_lang,
    toggle_blocked,
    toggle_notify,
    whitelist_count,
)
from i18n import _, activate_owner_lang, detect_language, set_lang
from keyboards import back_to_group_kb, group_menu_kb, groups_kb, types_kb

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


async def _owner_only(pool, chat_id: int, user_id: int) -> bool:
    return await get_owner(pool, chat_id) == user_id


async def _deny(cb: CallbackQuery) -> None:
    await cb.answer(texts.NOT_OWNER(), show_alert=True)


async def _group_title(pool, owner_id: int, chat_id: int) -> str:
    for cid, title in await owner_groups(pool, owner_id):
        if cid == chat_id:
            return title or str(chat_id)
    return str(chat_id)


def _parse_chat(data: str) -> int:
    return int(data.split(":", 1)[1])


def _lang_toggle(lang: str) -> tuple[str, str]:
    if lang == "ru":
        return (texts.LANG_BUTTON_EN(), "lang:en")
    return (texts.LANG_BUTTON_RU(), "lang:ru")


async def _start_screen(pool, owner_id: int, tg_code: str | None):
    stored = await get_owner_lang(pool, owner_id)
    lang = stored or detect_language(tg_code)
    if stored is None:
        await set_owner_lang(pool, owner_id, lang)
    set_lang(lang)
    groups = await owner_groups(pool, owner_id)
    if groups:
        text = texts.START() + "\n\n" + texts.MY_GROUPS()
    else:
        text = texts.START() + "\n\n" + texts.GROUPS_EMPTY()
    return text, groups_kb(groups, lang_toggle=_lang_toggle(lang))


@router.message(Command("start"))
async def on_start(message: Message, pool) -> None:
    owner_id = message.from_user.id
    try:
        from handlers_membership import flush_pending

        await flush_pending(pool, message.bot, owner_id)
    except ImportError:
        pass
    text, kb = await _start_screen(
        pool, owner_id, getattr(message.from_user, "language_code", None)
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "back_groups")
async def on_back_groups(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    text, kb = await _start_screen(
        pool, cb.from_user.id, getattr(cb.from_user, "language_code", None)
    )
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("lang:"))
async def on_language(cb: CallbackQuery, pool) -> None:
    lang = cb.data.split(":", 1)[1]
    await set_owner_lang(pool, cb.from_user.id, lang if lang in ("en", "ru") else "en")
    text, kb = await _start_screen(
        pool, cb.from_user.id, getattr(cb.from_user, "language_code", None)
    )
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("group:"))
async def on_group_selected(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    title = await _group_title(pool, cb.from_user.id, chat_id)
    await cb.message.edit_text(
        texts.GROUP_TITLE(title),
        reply_markup=group_menu_kb(
            chat_id,
            n_blocked=len(await get_blocked(pool, chat_id)),
            n_white=await whitelist_count(pool, chat_id),
            notify_enabled=await get_notify(pool, chat_id),
        ),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("types:"))
async def on_types_list(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await cb.message.edit_text(
        _("Blocked types for {title} (tap to toggle):\n{note}").format(
            title=await _group_title(pool, cb.from_user.id, chat_id),
            note=texts.COMMANDS_EXEMPT_NOTE(),
        ),
        reply_markup=types_kb(chat_id, await get_blocked(pool, chat_id)),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def on_toggle(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    blocked = await toggle_blocked(pool, chat_id, ctype)
    await cb.message.edit_text(
        _("Blocked types for {title} (tap to toggle):\n{note}").format(
            title=await _group_title(pool, cb.from_user.id, chat_id),
            note=texts.COMMANDS_EXEMPT_NOTE(),
        ),
        reply_markup=types_kb(chat_id, blocked),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("stats:"))
async def on_stats(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    stats = await get_stats(pool, chat_id)
    body = format_stats(stats)
    if body == format_stats({}):
        body = texts.STATS_EMPTY(await _group_title(pool, cb.from_user.id, chat_id))
    else:
        body = f"{await _group_title(pool, cb.from_user.id, chat_id)}: {body}"
    await cb.message.edit_text(body, reply_markup=back_to_group_kb(chat_id))
    await cb.answer()


@router.callback_query(F.data.startswith("reset_stats:"))
async def on_reset_stats(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await reset_stats(pool, chat_id)
    await cb.message.edit_text(_("Stats cleared."))
    await cb.answer()


@router.callback_query(F.data.startswith("reset_group:"))
async def on_reset_group(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    parts = cb.data.split(":")
    chat_id = int(parts[1])
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    if len(parts) == 3 and parts[2] == "confirm":
        await reset_group_data(pool, chat_id)
        await cb.message.edit_text(_("Group data cleared. Everything is allowed again."))
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(
            text=_("Yes, clear it"), callback_data=f"reset_group:{chat_id}:confirm"
        )
        builder.button(text=_("Cancel"), callback_data=f"group:{chat_id}")
        builder.adjust(1)
        await cb.message.edit_text(
            _("Clear blocked types, whitelist and stats for this group?"),
            reply_markup=builder.as_markup(),
        )
    await cb.answer()


async def render_group_menu(pool, owner_id: int, chat_id: int):
    """Shared group-menu render used by the whitelist router's Back button."""
    title = await _group_title(pool, owner_id, chat_id)
    return (
        texts.GROUP_TITLE(title),
        group_menu_kb(
            chat_id,
            n_blocked=len(await get_blocked(pool, chat_id)),
            n_white=await whitelist_count(pool, chat_id),
            notify_enabled=await get_notify(pool, chat_id),
        ),
    )


@router.callback_query(F.data.startswith("notify:"))
async def on_notify(cb: CallbackQuery, pool) -> None:
    await activate_owner_lang(pool, cb.from_user)
    chat_id = _parse_chat(cb.data)
    if not await _owner_only(pool, chat_id, cb.from_user.id):
        await _deny(cb)
        return
    await toggle_notify(pool, chat_id)
    text, kb = await render_group_menu(pool, cb.from_user.id, chat_id)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()
