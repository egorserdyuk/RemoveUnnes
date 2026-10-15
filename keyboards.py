"""Keyboard builders returning plain Bot API markup dicts (no framework needed).

Callback prefixes (exact):
  group:{chat_id}  types:{chat_id}  toggle:{chat_id}:{ctype}
  white:{chat_id}  pick_users:{chat_id}  unwhite:{chat_id}:{user_id}
  notify:{chat_id}  stats:{chat_id}  lang:{en,ru}
  reset_stats:{chat_id}  reset_group:{chat_id}  reset_group:{chat_id}:confirm
  back_groups
"""

from classify import CONTENT_TYPES
from i18n import _, n


def _inline(*rows: list[dict]) -> dict:
    return {"inline_keyboard": [[dict(b) for b in row] for row in rows]}


def _btn(text: str, callback_data: str) -> dict:
    return {"text": text, "callback_data": callback_data}


def groups_kb(
    groups: list[tuple[int, str]], lang_toggle: tuple[str, str] | None = None
) -> dict:
    rows = [[{"text": title or str(chat_id), "callback_data": f"group:{chat_id}"}]
            for chat_id, title in groups]
    if lang_toggle is not None:
        rows.append([{"text": lang_toggle[0], "callback_data": lang_toggle[1]}])
    return {"inline_keyboard": rows}


def group_menu_kb(
    chat_id: int, n_blocked: int, n_white: int, notify_enabled: bool = False
) -> dict:
    return _inline(
        [_btn(_("Blocked types: {n}").format(n=n_blocked), f"types:{chat_id}")],
        [_btn(n("Whitelist: {n} user", "Whitelist: {n} users", n_white).format(n=n_white),
              f"white:{chat_id}")],
        [_btn(_("Notifications: ON") if notify_enabled else _("Notifications: OFF"),
              f"notify:{chat_id}")],
        [_btn(_("Stats"), f"stats:{chat_id}")],
        [_btn(_("Reset stats"), f"reset_stats:{chat_id}")],
        [_btn(_("Remove group data"), f"reset_group:{chat_id}")],
        [_btn(_("« My groups"), "back_groups")],
    )


def types_kb(chat_id: int, blocked: set[str]) -> dict:
    rows = []
    row: list[dict] = []
    for ctype in CONTENT_TYPES:
        mark = "✅" if ctype in blocked else "❌"
        row.append(_btn(f"{mark} {ctype}", f"toggle:{chat_id}:{ctype}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn(_("« Back"), f"group:{chat_id}")])
    return {"inline_keyboard": rows}


def whitelist_kb(chat_id: int, users: list[tuple[int, str | None]]) -> dict:
    rows = []
    for user_id, username in users:
        label = f"@{username}" if username else str(user_id)
        rows.append([_btn(f"✖ {label}", f"unwhite:{chat_id}:{user_id}")])
    rows.append([_btn(_("+ Add via picker"), f"pick_users:{chat_id}")])
    rows.append([_btn(_("« Back"), f"group:{chat_id}")])
    return {"inline_keyboard": rows}


def back_to_group_kb(chat_id: int) -> dict:
    return _inline([_btn(_("« Back"), f"group:{chat_id}")])


def confirm_reset_kb(chat_id: int) -> dict:
    return _inline(
        [_btn(_("Yes, clear it"), f"reset_group:{chat_id}:confirm")],
        [_btn(_("Cancel"), f"group:{chat_id}")],
    )


def picker_kb(request_id: int) -> dict:
    return {
        "keyboard": [
            [
                {
                    "text": _("Pick users"),
                    "request_users": {
                        "request_id": request_id,
                        "user_is_bot": False,
                        "max_quantity": 10,
                        "request_name": True,
                        "request_username": True,
                    },
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_reply_kb() -> dict:
    return {"remove_keyboard": True}
