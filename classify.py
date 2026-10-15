"""Single content-type classification for incoming messages."""

CONTENT_TYPES: list[str] = [
    "story_forward",
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
    "text",
]

# Bot API message attribute backing each content type.
_FIELD_BY_TYPE: tuple[tuple[str, str], ...] = (
    ("story_forward", "story"),
    ("photo", "photo"),
    ("video", "video"),
    ("video_note", "video_note"),
    ("voice", "voice"),
    ("audio", "audio"),
    ("document", "document"),
    ("animation", "animation"),
    ("sticker", "sticker"),
    ("poll", "poll"),
    ("contact", "contact"),
    ("location", "location"),
    ("venue", "venue"),
    ("dice", "dice"),
    ("game", "game"),
    ("invoice", "invoice"),
    ("successful_payment", "successful_payment"),
    ("checklist", "checklist"),
    ("text", "text"),
)

def _is_service(message) -> bool:
    for attr in (
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
        if getattr(message, attr, None):
            return True
    return False


def classify(message) -> str | None:
    """Return one content type, or None for service/unknown messages."""
    if _is_service(message):
        return None
    for ctype, field in _FIELD_BY_TYPE:
        if getattr(message, field, None):
            return ctype
    return None


def is_command_exempt(message) -> bool:
    """True for /bot commands at the start (other bots keep working)."""
    text = getattr(message, "text", None) or ""
    if not text.startswith("/"):
        return False
    for entity in getattr(message, "entities", None) or []:
        e_type = entity.type if hasattr(entity, "type") else entity.get("type")
        offset = entity.offset if hasattr(entity, "offset") else entity.get("offset")
        if e_type == "bot_command" and offset == 0:
            return True
    return False
