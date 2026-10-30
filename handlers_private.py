"""Private-chat handlers: /start, group list, per-group config, stats, language."""

import texts
from adapters import is_start_command
from db import (
    clear_limit,
    format_stats,
    get_blocked,
    get_limit,
    get_limits,
    get_notify,
    get_owner,
    get_owner_lang,
    get_stats,
    owner_groups,
    reset_group_data,
    reset_stats,
    set_limit,
    set_owner_lang,
    toggle_blocked,
    toggle_notify,
    whitelist_count,
)
from i18n import _, activate_owner_lang, detect_language, set_lang
from keyboards import (
    back_to_group_kb,
    confirm_reset_kb,
    group_menu_kb,
    groups_kb,
    limit_detail_kb,
    limits_list_kb,
    types_kb,
)
from limits import format_window, parse_window

_pending_limits: dict[int, tuple[int, str, str]] = {}


async def _owner_only(pool, chat_id: int, user_id: int) -> bool:
    return await get_owner(pool, chat_id) == user_id


async def _deny(app, cb) -> None:
    await cb.answer(texts.NOT_OWNER(), alert=True)


async def _group_title(pool, owner_id: int, chat_id: int) -> str:
    for cid, title in await owner_groups(pool, owner_id):
        if cid == chat_id:
            return title or str(chat_id)
    return str(chat_id)


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


async def on_start(pool, app, msg) -> None:
    owner_id = msg.from_id
    try:
        from handlers_membership import flush_pending

        await flush_pending(pool, app, owner_id)
    except ImportError:
        pass
    sender = msg.get("from") or {}
    text, kb = await _start_screen(pool, owner_id, sender.get("language_code"))
    await app.send_msg(msg.chat_id, text, kbd=kb)


async def on_back_groups(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    text, kb = await _start_screen(pool, cb.from_id, getattr(cb, "language_code", None))
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()


def _tg_user(cb):
    from types import SimpleNamespace

    return SimpleNamespace(id=cb.from_id, language_code=getattr(cb, "language_code", None))


async def on_language(pool, app, cb) -> None:
    lang = cb.data.split(":", 1)[1]
    await set_owner_lang(pool, cb.from_id, lang if lang in ("en", "ru") else "en")
    text, kb = await _start_screen(pool, cb.from_id, getattr(cb, "language_code", None))
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()


async def on_group_selected(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    title = await _group_title(pool, cb.from_id, chat_id)
    text, kb = await render_group_menu(pool, cb.from_id, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, texts.GROUP_TITLE(title), kbd=kb)
    await cb.answer()


async def _types_screen(pool, owner_id: int, chat_id: int):
    title = await _group_title(pool, owner_id, chat_id)
    text = _("Blocked types for {title} (tap to toggle):\n{note}").format(
        title=title, note=texts.COMMANDS_EXEMPT_NOTE()
    )
    return text, types_kb(chat_id, await get_blocked(pool, chat_id))


async def on_types_list(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    text, kb = await _types_screen(pool, cb.from_id, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()


async def on_toggle(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await toggle_blocked(pool, chat_id, ctype)
    text, kb = await _types_screen(pool, cb.from_id, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()


async def on_stats(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    stats = await get_stats(pool, chat_id)
    body = format_stats(stats)
    if body == format_stats({}):
        body = texts.STATS_EMPTY(await _group_title(pool, cb.from_id, chat_id))
    else:
        body = f"{await _group_title(pool, cb.from_id, chat_id)}: {body}"
    await app.edit_msg(cb.chat_id, cb.msg_id, body, kbd=back_to_group_kb(chat_id))
    await cb.answer()


async def on_reset_stats(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await reset_stats(pool, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, _("Stats cleared."))
    await cb.answer()


async def on_reset_group(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    parts = cb.data.split(":")
    chat_id = int(parts[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    if len(parts) == 3 and parts[2] == "confirm":
        await reset_group_data(pool, chat_id)
        await app.edit_msg(
            cb.chat_id, cb.msg_id, _("Group data cleared. Everything is allowed again.")
        )
    else:
        await app.edit_msg(
            cb.chat_id,
            cb.msg_id,
            _("Clear blocked types, whitelist and stats for this group?"),
            kbd=confirm_reset_kb(chat_id),
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


async def on_notify(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await toggle_notify(pool, chat_id)
    text, kb = await render_group_menu(pool, cb.from_id, chat_id)
    await app.edit_msg(cb.chat_id, cb.msg_id, text, kbd=kb)
    await cb.answer()


def _limit_detail_text(ctype: str, dur: int | None, cool: int | None) -> str:
    return f"{ctype}: max duration {format_window(dur)}, cooldown {format_window(cool)}"


async def on_limits_list(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    chat_id = int(cb.data.split(":", 1)[1])
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    title = await _group_title(pool, cb.from_id, chat_id)
    limits = await get_limits(pool, chat_id)
    await app.edit_msg(
        cb.chat_id, cb.msg_id, texts.LIMITS_TITLE(title), kbd=limits_list_kb(chat_id, limits)
    )
    await cb.answer()


async def on_limit_detail(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    dur, cool = await get_limit(pool, chat_id, ctype)
    await app.edit_msg(
        cb.chat_id,
        cb.msg_id,
        _limit_detail_text(ctype, dur, cool),
        kbd=limit_detail_kb(chat_id, ctype, dur, cool),
    )
    await cb.answer()


async def on_lim_dur(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    _pending_limits[cb.from_id] = (chat_id, ctype, "dur")
    await app.send_msg(cb.chat_id, texts.LIMIT_PROMPT_DUR())
    await cb.answer()


async def on_lim_cool(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    _pending_limits[cb.from_id] = (chat_id, ctype, "cool")
    await app.send_msg(cb.chat_id, texts.LIMIT_PROMPT_COOL())
    await cb.answer()


async def on_lim_clear(pool, app, cb) -> None:
    await activate_owner_lang(pool, _tg_user(cb))
    _prefix, chat_s, ctype = cb.data.split(":", 2)
    chat_id = int(chat_s)
    if not await _owner_only(pool, chat_id, cb.from_id):
        await _deny(app, cb)
        return
    await clear_limit(pool, chat_id, ctype)
    dur, cool = await get_limit(pool, chat_id, ctype)
    await app.edit_msg(
        cb.chat_id,
        cb.msg_id,
        _limit_detail_text(ctype, dur, cool),
        kbd=limit_detail_kb(chat_id, ctype, dur, cool),
    )
    await cb.answer()


async def _consume_pending_limit(pool, app, msg) -> bool:
    """Handle a private text as a pending limit value. Returns True if consumed."""
    pending = _pending_limits.get(msg.from_id)
    if pending is None:
        return False
    text = msg.text
    if not isinstance(text, str) or not text.strip():
        return False
    chat_id, ctype, field = pending
    try:
        value = parse_window(text)
    except ValueError:
        await app.send_msg(msg.chat_id, texts.LIMIT_BAD_VALUE())
        return True
    dur, cool = await get_limit(pool, chat_id, ctype)
    if field == "dur":
        dur = value
    else:
        cool = value
    await set_limit(pool, chat_id, ctype, dur, cool)
    del _pending_limits[msg.from_id]
    await app.send_msg(msg.chat_id, texts.LIMIT_SET_OK())
    return True


async def route_private(pool, app, msg) -> None:
    """Route a private-chat message: users_shared picker result or /start."""
    if msg.chat_type != "private":
        return
    if msg.get("users_shared"):
        from handlers_whitelist import on_users_shared

        await on_users_shared(pool, app, msg)
        return
    if is_start_command(msg.text):
        _pending_limits.pop(msg.from_id, None)
        await on_start(pool, app, msg)
        return
    await _consume_pending_limit(pool, app, msg)


async def route_cb(pool, app, cb) -> None:
    """Route a callback query by data prefix."""
    from handlers_whitelist import on_pick_users, on_unwhite, on_white_list

    data = cb.data or ""
    if data.startswith("group:"):
        await on_group_selected(pool, app, cb)
    elif data.startswith("types:"):
        await on_types_list(pool, app, cb)
    elif data.startswith("toggle:"):
        await on_toggle(pool, app, cb)
    elif data.startswith("white:"):
        await on_white_list(pool, app, cb)
    elif data.startswith("pick_users:"):
        await on_pick_users(pool, app, cb)
    elif data.startswith("unwhite:"):
        await on_unwhite(pool, app, cb)
    elif data.startswith("notify:"):
        await on_notify(pool, app, cb)
    elif data.startswith("stats:"):
        await on_stats(pool, app, cb)
    elif data.startswith("reset_stats:"):
        await on_reset_stats(pool, app, cb)
    elif data.startswith("reset_group:"):
        await on_reset_group(pool, app, cb)
    elif data.startswith("limits:"):
        await on_limits_list(pool, app, cb)
    elif data.startswith("lim_dur:"):
        await on_lim_dur(pool, app, cb)
    elif data.startswith("lim_cool:"):
        await on_lim_cool(pool, app, cb)
    elif data.startswith("lim_clear:"):
        await on_lim_clear(pool, app, cb)
    elif data.startswith("lim:"):
        await on_limit_detail(pool, app, cb)
    elif data == "back_groups":
        await on_back_groups(pool, app, cb)
    elif data.startswith("lang:"):
        await on_language(pool, app, cb)
    else:
        await cb.answer()


def register(app, pool) -> None:
    async def _msg(msg):
        await route_private(pool, app, msg)

    async def _cb(cb):
        await route_cb(pool, app, cb)

    app.on_msg(_msg)
    app.on_cb(_cb)
