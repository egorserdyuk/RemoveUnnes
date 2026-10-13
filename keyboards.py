"""Inline/reply keyboard builders + callback-data protocol.

Callback prefixes (exact):
  group:{chat_id}  types:{chat_id}  toggle:{chat_id}:{ctype}
  white:{chat_id}  pick_users:{chat_id}  unwhite:{chat_id}:{user_id}  stats:{chat_id}
  reset_stats:{chat_id}  reset_group:{chat_id}  reset_group:{chat_id}:confirm
  notify:{chat_id}  back_groups
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from classify import CONTENT_TYPES
from i18n import _, n


def groups_kb(
    groups: list[tuple[int, str]], lang_toggle: tuple[str, str] | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chat_id, title in groups:
        builder.button(text=title or str(chat_id), callback_data=f"group:{chat_id}")
    if lang_toggle is not None:
        builder.button(text=lang_toggle[0], callback_data=lang_toggle[1])
    builder.adjust(1)
    return builder.as_markup()


def group_menu_kb(chat_id: int, n_blocked: int, n_white: int, notify_enabled: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=_("Blocked types: {n}").format(n=n_blocked), callback_data=f"types:{chat_id}"
    )
    builder.button(
        text=n("Whitelist: {n} user", "Whitelist: {n} users", n_white).format(n=n_white),
        callback_data=f"white:{chat_id}",
    )
    builder.button(
        text=_("Notifications: ON") if notify_enabled else _("Notifications: OFF"),
        callback_data=f"notify:{chat_id}",
    )
    builder.button(text=_("Stats"), callback_data=f"stats:{chat_id}")
    builder.button(text=_("Reset stats"), callback_data=f"reset_stats:{chat_id}")
    builder.button(text=_("Remove group data"), callback_data=f"reset_group:{chat_id}")
    builder.button(text=_("« My groups"), callback_data="back_groups")
    builder.adjust(1)
    return builder.as_markup()


def types_kb(chat_id: int, blocked: set[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ctype in CONTENT_TYPES:
        mark = "✅" if ctype in blocked else "❌"
        builder.button(text=f"{mark} {ctype}", callback_data=f"toggle:{chat_id}:{ctype}")
    builder.button(text=_("« Back"), callback_data=f"group:{chat_id}")
    builder.adjust(2)
    return builder.as_markup()


def whitelist_kb(chat_id: int, users: list[tuple[int, str | None]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, username in users:
        label = f"@{username}" if username else str(user_id)
        builder.button(text=f"✖ {label}", callback_data=f"unwhite:{chat_id}:{user_id}")
    builder.button(text=_("+ Add via picker"), callback_data=f"pick_users:{chat_id}")
    builder.button(text=_("« Back"), callback_data=f"group:{chat_id}")
    builder.adjust(1)
    return builder.as_markup()


def picker_kb(request_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(
        text=_("Pick users"),
        request_users=KeyboardButtonRequestUsers(
            request_id=request_id,
            user_is_bot=False,
            max_quantity=10,
            request_name=True,
            request_username=True,
        ),
    )
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def remove_reply_kb():
    from aiogram.types import ReplyKeyboardRemove

    return ReplyKeyboardRemove()
