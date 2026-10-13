"""English UI copy for the bot."""

START = (
    "Hi! I remove unwanted media from your groups.\n\n"
    "1. Add me to a group as admin with the Delete Messages right.\n"
    "2. Come back here and pick the group to choose which message types I delete "
    "and who is whitelisted.\n\n"
    "By default everything is allowed — nothing is deleted until you block a type."
)

GROUPS_EMPTY = "You have no groups yet. Add me to a group first, then come back here."

MY_GROUPS = "Your groups:"

GROUP_TITLE = "Settings for {title}"

NEED_ADMIN = (
    "I need admin rights with Delete Messages permission in {title} "
    "to remove messages. Please promote me and I will continue."
)

NOT_OWNER = "Only the person who added me here can change this."

CONNECTED = (
    "Connected to {title}. Pick it below to choose blocked types, "
    "manage the whitelist, or see stats."
)

STATS_EMPTY = "Nothing removed yet in {title}."

COMMANDS_EXEMPT_NOTE = "Note: /commands of other bots always pass through."
