# Telegram Media Remover Bot — Design

Date: 2026-10-13
Stack: Python, aiogram 3.31.0 (pinned), PostgreSQL, long polling
Language of bot UI: English

## Intent and the why

Group chats get spammed with unwanted media types (voice/audio messages,
video circles, photos, videos, GIFs, stickers, text, etc.). Normal Telegram
group restrictions cannot help because some senders are admins — restricting
them would mean demoting them, which owners don't want.

This bot sits *above* Telegram permissions: when added to a group as admin
with delete rights, it silently deletes messages whose content type is
blocked for that group, regardless of whether the sender is a regular member
or an admin. Only explicitly whitelisted users bypass the blocks.

Success = blocked types disappear from the group with no noise in the group,
owner sees private per-group counters like
`removed messages: 1 photo; 2 videos; 7 animations; 11 stickers`,
and non-blocked types always pass through.

## Goals

- Private `/start` flow: bot explains it must be added to a group chat.
- Track every group the owner added the bot to; show them as separate
  buttons (2/3/more) in private chat.
- Per-group settings (isolated):
  - blocked content types, default = everything allowed (nothing blocked);
  - whitelist of user IDs, default empty, unlimited size, per-group;
  - removal counters per content type, visible only to the owner in private.
- Silent removal in group: delete only, no message to the group at all.
- Owner-only control and stats: only the person who started the bot and
  added it to that group can change that group's settings or see its stats.
- Whitelist management via Telegram native user selection:
  ReplyKeyboard `KeyboardButton(request_users=KeyboardButtonRequestUsers(...))`
  (`user_is_bot=False`, `max_quantity=10` per pick, repeatable for unlimited),
  handling `F.users_shared`, plus per-user Remove buttons.
  Docs: aiogram 3.31 `KeyboardButtonRequestUsers(request_id, user_is_bot,
  max_quantity, request_name/username/photo)`, `UsersShared` service message,
  private-chat-only button.
- Content-type coverage: all real Telegram message content types, each
  individually blockable (owner approved "them all"):
  `text, photo, video, video_note (circles), voice, audio, document,
  animation (GIF), sticker, poll, contact, location, venue, dice,
  game, invoice, successful_payment, story_forward, checklist`
  (final list = every `aiogram.types.Message` media field the builder finds
  in 3.31; service messages like `new_chat_members`, `left_chat_member`,
  `pinned_message`, `chat_shared`, `users_shared` are NEVER deleted).
- If bot cannot delete (not admin / no `can_delete_messages`), skip deletion
  and DM the owner once per group per incident window:
  "I need admin + delete rights in <group>".
- Persistent PostgreSQL storage so restart keeps settings + counters.

## Non-goals

- No warnings / mutes / bans / timed restrictions — delete only.
- No global whitelist or global block list — everything is per-group.
- No per-user rate limits, no AI/spam-text detection, no keyword filters.
- No group-visible logs or commands (`!stats` in group, etc.).
- No multi-owner or role delegation for one group.
- No webhook deployment in v1 (polling only, simplest).

## Anti-goals

- Must NOT post anything into the group on deletion (not even "removed").
- Must NOT leak one group's stats/settings to another group or to non-owners.
- Must NOT delete Telegram service messages or its own admin notices.
- Must NOT cap the whitelist.

## Constraints (decided)

- `aiogram==3.31.0` pinned (repo already has this in `requirements.txt`).
  Use v3 patterns: `Router`, `F.*` magic filters (`F.photo`, `F.video`,
  `F.text`, ...), `ReplyKeyboardBuilder` / `InlineKeyboardBuilder`,
  `my_chat_member` router for add/remove tracking, `bot.delete_message`
  / `bot.delete_messages`. Catch-all group handler is bare
  `@router.message()` + manual `classify(message) -> content_type`, NOT
  dozens of `F.*` handlers, so classification stays in one place.
- DB: PostgreSQL, lightweight + async. Builder picks exact lib
  (suggestion: `asyncpg` direct + tiny `*_init.sql`, or SQLAlchemy Core async;
  no Alembic in v1 — `CREATE TABLE IF NOT EXISTS` on startup).
  Required env: `BOT_TOKEN`, `POSTGRES_DSN` (e.g.
  `postgresql://user:pass@localhost:5432/remover`).
- Bot must be added as group admin with Delete Messages right; otherwise it
  DMs the owner and does nothing else.
- English button/text copy only in v1.
- `request_users` buttons work in private chats only — whitelist add flow
  lives in private chat (confirmed workable per aiogram 3.31 docs).

## Agreed flows (decided)

### A. Private /start
- `/start` → text: "Add me to a group where you want spam removed. Add me as
  admin with Delete rights, then come back here to configure."
  + button `My groups` (also show group list directly if any).
- Group list: one `InlineKeyboardButton` per group
  (`Select group <id>` → `group:{chat_id}`), title from stored `chat.title`.

### B. Bot added to / removed from group
- Router `my_chat_member`: on `new_chat_member.status in {member, administrator}`
  for our bot → upsert `groups(chat_id, owner_id=event.from_user.id, title)`,
  DM owner: "Connected to <title>. Pick it below to block types / whitelist."
- On `left`/`kicked` → keep settings/CT+stats (so re-add restores) — builder
  default; owner can delete group data via `Remove group data` button.
  Note: `my_chat_member.from_user` is the inviter; that user becomes owner.
  If added by someone who never ran `/start`, bot still records them as owner
  and they get the DM on first `/start` (lookup by owner_id).
- DECIDED (owner question): if the bot is re-added by a *different* user,
  ownership transfers with a **fresh start** — all per-group rows
  (`blocked`, `whitelist`, `stats`) are wiped and `groups.owner_id` is set
  to the new inviter. Re-add by the *same* owner keeps existing settings.
- DECIDED (BotFather, builder call): Group Privacy must be OFF in BotFather
  or the group handler never sees normal messages. Setup docs must include
  this + "make the bot admin with Delete Messages right". Bot startup logs
  `allowed_updates` including `message, edited_message, my_chat_member`.
- DECIDED (no-DM case, builder call): Telegram forbids DMing users who never
  ran `/start`. Membership handler wraps the hello-DM in
  try/except `TelegramForbiddenError` and leaves a pending row; first
  `/start` from that `owner_id` flushes "Connected to <title>..." for all
  pending groups.

### C. Group message handling
- Single handler for `chat.type in {group, supergroup}`, skipping service
  messages and messages from the bot itself. Handles both `message` and
  `edited_message` with the same function (DECIDED, builder call — otherwise
  blocking is bypassed by send-allowed-then-edit).
- Steps: `ctype = classify(message)` → if `ctype is None` (service/unknown)
  return → if `sender in whitelist(chat_id)` return → if
  `ctype in blocked(chat_id)` → `await bot.delete_message(chat, msg)` +
  `incr_stat(chat_id, ctype)` → on `TelegramBadRequest` (no rights) → DM owner
  (throttled: max 1 DM per group per 10 min, builder's call).
- DECIDED (anonymous/channel, owner pick): messages with no `from_user`
  (anonymous admins, channel posts via `sender_chat`) cannot match the
  whitelist and are judged **by type only** — deleted if that type is
  blocked, allowed otherwise. Bot's own messages are always skipped.
- DECIDED (text vs commands, owner pick): when `text` is blocked, messages
  starting with `/` whose entities contain `bot_command` at offset 0 are
  **exempt** (never deleted), so other bots keep working. All other text is
  deleted.
- `classify` priority (a message has exactly one type; caption does NOT make
  it `text`): check in order
  `story_forward → photo → video → video_note → voice → audio → document →
  animation → sticker → poll → contact → location → venue → dice → game →
  invoice → successful_payment → checklist → text`
  (text last so captioned media counts as media). Builder to verify field
  names against aiogram 3.31 `Message` (`message.story`, `message.photo`,
  `message.video`, `message.video_note`, `message.voice`, `message.audio`,
  `message.document`, `message.animation`, `message.sticker`, `message.poll`,
  `message.contact`, `message.location`, `message.venue`, `message.dice`,
  `message.game`, `message.invoice`, `message.successful_payment`,
  `message.checklist`, `message.text`).

### D. Private group-config screen (approved layout)
After tapping a group → message with:
- `Blocked types: N` → opens toggle list (inline buttons per type
  `✅ photo / ❌ photo`, callback `toggle:{chat_id}:{ctype}`), paginated if
  needed; `Back`.
- `Whitelist: N users` → shows current list (username or id) each with
  `Remove` (`unwhite:{chat_id}:{user_id}`) + `+ Add via picker` button that
  sends a ReplyKeyboard with `KeyboardButton(text="Pick users",
  request_users=KeyboardButtonRequestUsers(request_id=<unique>,
  user_is_bot=False, max_quantity=10, request_name=True,
  request_username=True))`. Incoming `F.users_shared` adds all
  `users_shared.users[*].user_id`. Repeatable → unlimited.
- `Stats` → `removed messages: 1 photo; 2 videos; 7 animations; 11 stickers`
  (only non-zero types, or "nothing removed yet"), per-group.
- `Reset stats`, `Remove group data`, `« My groups`.
- DECIDED (`Remove group data` while still joined, builder call): wipes
  `blocked` + `whitelist` + `stats` for that group but keeps the `groups` row
  and stays joined — i.e. reset to fresh defaults. Full row removal happens
  only via re-add-by-other (fresh-start transfer) or manual DB delete.

### E. Stats visibility
- Shown only in private chat to that group's owner, on demand via `Stats`
  button (no auto-DM per deletion — avoids DM spam). Builder may add
  optional digest later, not v1.

## DB sketch (builder finalizes)

Tables (all `IF NOT EXISTS`):
- `owners(user_id BIGINT PK, created_at TIMESTAMPTZ DEFAULT now())`
- `groups(chat_id BIGINT PK, owner_id BIGINT NOT NULL, title TEXT,
  added_at TIMESTAMPTZ DEFAULT now())`
- `blocked(chat_id BIGINT, ctype TEXT, PRIMARY KEY(chat_id, ctype))`
  (absence = allowed; default empty = all allowed)
- `whitelist(chat_id BIGINT, user_id BIGINT, username TEXT, display TEXT,
  added_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY(chat_id, user_id))`
- `stats(chat_id BIGINT, ctype TEXT, cnt BIGINT DEFAULT 0,
  PRIMARY KEY(chat_id, ctype))`
- Optional `meta` for DM throttle
  (`no_rights_notified_at(chat_id PK, at TIMESTAMPTZ)`).

Suggested files (builder may reshape):
`bot.py (entry, polling), config.py (env), db.py (asyncpg pool + queries),
keyboards.py, handlers_private.py, handlers_group.py, handlers_membership.py,
classify.py, texts.py`. Single requirements addition: `asyncpg`
(or SQLAlchemy async) + existing `aiogram==3.31.0`.

## What's left to the builder (explicit)

- Exact PG driver + DDL + `classify()` field verification vs aiogram 3.31.
- Polling startup (`await dp.start_polling(bot, allowed_updates=...)`),
  `allowed_updates` set including `message, my_chat_member`.
- Callback-data prefixes, pagination of type list, DM throttle window.
- `Remove group data` confirm step, title refresh on `my_chat_member`.
- Error copy for "need admin rights" DM and for non-owner taps
  ("Only the person who added me here can change this.").
- Local run: `docker compose` for Postgres or DSN docs — builder's call.
