"""Adapt goygram event objects to the plain field namespaces the core logic uses."""

from types import SimpleNamespace


def _get(msg, key):
    get = getattr(msg, "get", None)
    if callable(get):
        try:
            return get(key)
        except Exception:
            return None
    raw = getattr(msg, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key)
    return getattr(msg, key, None)


def message_fields(msg) -> SimpleNamespace:
    """Flatten a goygram message into getattr-able fields for classify()."""
    from_user = _get(msg, "from") or {}
    chat = _get(msg, "chat") or {}
    fields = {
        "message_id": getattr(msg, "msg_id", None),
        "chat": {"id": getattr(msg, "chat_id", None), "type": getattr(msg, "chat_type", None)},
        "from_user": SimpleNamespace(
            id=getattr(msg, "from_id", None),
            username=from_user.get("username") if isinstance(from_user, dict) else None,
            first_name=from_user.get("first_name") if isinstance(from_user, dict) else None,
        )
        if getattr(msg, "from_id", None) is not None
        else None,
        "sender_chat": _get(msg, "sender_chat"),
        "text": getattr(msg, "text", None) or None,
        "entities": _get(msg, "entities") or [],
        "chat_title": chat.get("title") if isinstance(chat, dict) else None,
    }
    for key in (
        "story",
        "photo",
        "video",
        "video_note",
        "voice",
        "audio",
        "document",
        "animation",
        "sticker",
        "poll",
        "contact",
        "location",
        "venue",
        "dice",
        "game",
        "invoice",
        "successful_payment",
        "checklist",
        "new_chat_members",
        "left_chat_member",
        "new_chat_title",
        "new_chat_photo",
        "delete_chat_photo",
        "group_chat_created",
        "supergroup_chat_created",
        "channel_chat_created",
        "message_auto_delete_timer_changed",
        "pinned_message",
        "chat_shared",
        "users_shared",
        "forum_topic_created",
        "forum_topic_closed",
        "forum_topic_reopened",
        "forum_topic_edited",
        "general_forum_topic_hidden",
        "general_forum_topic_unhidden",
        "giveaway",
        "giveaway_completed",
        "video_chat_started",
        "video_chat_ended",
        "video_chat_participants_invited",
        "proximity_alert_triggered",
    ):
        fields[key] = _get(msg, key)
    return SimpleNamespace(**fields)


def is_start_command(text: str | None) -> bool:
    """True for /start with optional @bot suffix and args."""
    if not text:
        return False
    parts = text.strip().split()
    if not parts:
        return False
    first = parts[0].split("@")[0]
    return first == "/start"


def shared_users(msg) -> tuple[int | None, list[tuple[int, str | None, str | None]]]:
    """Parse a users_shared service payload: (request_id, [(id, username, display)])."""
    shared = _get(msg, "users_shared") or {}
    users = shared.get("users") or []
    rows = []
    for user in users:
        first = user.get("first_name") or ""
        last = user.get("last_name") or ""
        rows.append((user.get("user_id"), user.get("username"), f"{first} {last}".strip() or None))
    return shared.get("request_id"), rows
