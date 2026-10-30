"""English msgids for all user-visible copy (translated via i18n_ru.py)."""

from i18n import _


def START() -> str:
    return _(
        "Hi! I remove unwanted media from your groups.\n\n"
        "1. Add me to a group as admin with the Delete Messages right.\n"
        "2. Come back here and pick the group to choose which message types I delete "
        "and who is whitelisted.\n\n"
        "By default everything is allowed — nothing is deleted until you block a type."
    )


def GROUPS_EMPTY() -> str:
    return _("You have no groups yet. Add me to a group first, then come back here.")


def MY_GROUPS() -> str:
    return _("Your groups:")


def GROUP_TITLE(title: str) -> str:
    return _("Settings for {title}").format(title=title)


def NEED_ADMIN(title: str) -> str:
    return _(
        "I need admin rights with Delete Messages permission in {title} "
        "to remove messages. Please promote me and I will continue."
    ).format(title=title)


def NOT_OWNER() -> str:
    return _("Only the person who added me here can change this.")


def CONNECTED(title: str) -> str:
    return _(
        "Connected to {title}. Pick it below to block types, "
        "manage the whitelist, or see stats."
    ).format(title=title)


def STATS_EMPTY(title: str) -> str:
    return _("Nothing removed yet in {title}.").format(title=title)


def COMMANDS_EXEMPT_NOTE() -> str:
    return _("Note: /commands of other bots always pass through.")


def LANG_BUTTON_EN() -> str:
    return _("🌐 English")


def LANG_BUTTON_RU() -> str:
    return _("🌐 Русский")


def LIMITS_BUTTON() -> str:
    return _("Limits")


def LIMITS_TITLE(title: str) -> str:
    return _("Limits for {title} (tap a type):").format(title=title)


def LIMIT_PROMPT_DUR() -> str:
    return _("Send max duration as 30s/1m/1h/1d or off")


def LIMIT_PROMPT_COOL() -> str:
    return _("Send cooldown as 30s/1m/1h/1d or off")


def LIMIT_SET_OK() -> str:
    return _("Limit saved.")


def LIMIT_BAD_VALUE() -> str:
    return _("Bad value. Send like 30s/1m/1h/1d or off")
