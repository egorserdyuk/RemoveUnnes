"""Random deletion-notice phrases: mild insult + username + message type."""

import random

INSULTS: list[str] = [
    "jerk",
    "rascal",
    "sneaky fox",
    "rebel",
    "wise guy",
    "troublemaker",
    "smarty-pants",
    "menace",
]

NOTICE_TEMPLATES: list[str] = [
    "That {insult} {user} tried to send a {type}! Denied.",
    "{user} thought a {type} would sneak past me. Adorable. Deleted.",
    "Nice try, {user} — no {type}s allowed here.",
    "The {insult} {user} strikes again with a forbidden {type}!",
    "{user} tested the {type} filter. The filter won.",
    "A wild {type} from {user} appeared! I swept it away.",
    "{user}, sweetie, {type}s are banned here. Gone.",
    "Breaking news: {user}'s {type} didn't survive. What a {insult}.",
]

CONTENT_LABELS: dict[str, str] = {
    "story_forward": "forwarded story",
    "photo": "photo",
    "video": "video",
    "video_note": "video message",
    "voice": "voice message",
    "audio": "audio file",
    "document": "file",
    "animation": "GIF",
    "sticker": "sticker",
    "poll": "poll",
    "contact": "contact",
    "location": "location",
    "venue": "venue",
    "dice": "dice roll",
    "game": "game",
    "invoice": "invoice",
    "successful_payment": "payment",
    "checklist": "checklist",
    "text": "text message",
}


def render_notice(user: str, ctype: str, rng=random.choice) -> str:
    """Pick a random template + insult and fill in user and type label."""
    return rng(NOTICE_TEMPLATES).format(
        user=user, insult=rng(INSULTS), type=CONTENT_LABELS[ctype]
    )


def format_mention(sender) -> str:
    """@username, first name, or 'someone' for anonymous senders."""
    if sender is None:
        return "someone"
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    return getattr(sender, "first_name", None) or "someone"
