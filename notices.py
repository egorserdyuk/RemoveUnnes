"""Random deletion-notice phrases: mild insult + username + message type."""

import random

from i18n import _, msgid

INSULTS: list[str] = [
    msgid("jerk"),
    msgid("rascal"),
    msgid("sneaky fox"),
    msgid("rebel"),
    msgid("wise guy"),
    msgid("troublemaker"),
    msgid("smarty-pants"),
    msgid("menace"),
]

NOTICE_TEMPLATES: list[str] = [
    msgid("That {insult} {user} tried to send a {type}! Denied."),
    msgid("{user} thought a {type} would sneak past me. Adorable. Deleted."),
    msgid("Nice try, {user} — no {type} allowed here."),
    msgid("The {insult} {user} strikes again with a forbidden {type}!"),
    msgid("{user} tested the {type} filter. The filter won."),
    msgid("A wild {type} from {user} appeared! I swept it away."),
    msgid("{user}, sweetie, {type} are banned here. Gone."),
    msgid("Breaking news: {user}'s {type} didn't survive. What a {insult}."),
]

CONTENT_LABELS: dict[str, str] = {
    "story_forward": msgid("forwarded story"),
    "photo": msgid("photo"),
    "video": msgid("video"),
    "video_note": msgid("video message"),
    "voice": msgid("voice message"),
    "audio": msgid("audio file"),
    "document": msgid("file"),
    "animation": msgid("GIF"),
    "sticker": msgid("sticker"),
    "poll": msgid("poll"),
    "contact": msgid("contact"),
    "location": msgid("location"),
    "venue": msgid("venue"),
    "dice": msgid("dice roll"),
    "game": msgid("game"),
    "invoice": msgid("invoice"),
    "successful_payment": msgid("payment"),
    "checklist": msgid("checklist"),
    "text": msgid("text message"),
}


def render_notice(user: str, ctype: str, rng=random.choice) -> str:
    """Pick a random template + insult and fill in user and type label."""
    return _(rng(NOTICE_TEMPLATES)).format(
        user=user, insult=_(rng(INSULTS)), type=_(CONTENT_LABELS[ctype])
    )


def format_mention(sender) -> str:
    """@username, first name, or 'someone' for anonymous senders."""
    if sender is None:
        return _("someone")
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    return getattr(sender, "first_name", None) or _("someone")
