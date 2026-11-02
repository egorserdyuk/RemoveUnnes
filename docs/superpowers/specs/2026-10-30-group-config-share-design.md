# Group config share via base64 line — short design (2026-10-30)

## Intent / why
Let an owner copy all configured rules from one group to another via a single
copy-paste line, even to a group owned by a different user. Source owner taps
Export, sends the line to anyone; target owner taps Import and pastes it.

## Goals
- Export full setup for one chat: blocked types, per-type limits
  (max_duration_sec + cooldown_sec), notify_enabled, whitelist
  (user_id + username + display).
- Import overwrites target chat's setup so target ends identical to source.
- Line is self-contained (no chat_id/owner inside), shareable cross-user.
- Owner-only gating on both export and import (source and target).

## Non-goals
- Stats, owner, title, active flag, pending_greetings do NOT transfer.
- No merge mode, no partial import, no file upload, no QR.
- No encryption/signing — line is opaque but not secret.

## Anti-goals
- Import must never wipe target on bad input; validate first, then write.
- Must never let a deposed owner write via a stale pending import.

## Constraints
- Existing stack: Python, asyncpg, goygram, plain-dict keyboards.
- Bot API: callback_data ≤64B (so line travels in message text, not callback);
  private message ≤4096 chars (whitelist-heavy exports can be long — still one
  message, no chunking for v1).
- Follow existing patterns: `_pending_limits` pending-input flow in
  `handlers_private.py`, `activate_owner_lang`, `texts.py` + `i18n_ru.py` copy,
  callback prefixes documented in `keyboards.py`.
- Payload must validate against `classify.CONTENT_TYPES`,
  `limits.DURATION_TYPES` / `MAX_WINDOW_SEC`.

## Approaches
- **A — Buttons + paste (chosen).** `Export` / `Import` buttons in group menu.
  Export sends copyable code text. Import arms
  `_pending_imports[user_id] = chat_id`, next private text is consumed as config.
  Pros: smallest change, matches pending-limit UX, mobile-friendly.
- **B — /import <line> command arg (rejected).** Same payload, typed in one go.
  Cons: long strings truncate/split on mobile; still needs pending fallback.

## How (approach A, decided parts)
- New module `group_share.py` (pure, testable): `encode_config(blocked, limits,
  notify, whitelist) -> str`, `decode_config(line) -> dict` raising ValueError.
  Format: `json {v:1, blocked:sorted[], limits:{ctype:[dur,cool]},
  notify:bool, whitelist:[[uid,uname,disp]...]}` → utf-8 →
  `base64.urlsafe_b64encode` → `RMV1-<b64>` (strip padding on encode, restore on
  decode; strip whitespace/backticks/code-fence on decode).
- Validation on decode: v==1; blocked ⊆ CONTENT_TYPES; limits keys ⊆
  CONTENT_TYPES, dur/cool None or 0..MAX_WINDOW_SEC, dur only for
  DURATION_TYPES (reject otherwise); notify bool; whitelist list of
  [int, str|None, str|None], cap ~500 entries.
- DB: `get_group_config(pool, chat_id)` collects blocked/limits/notify/
  whitelist; `apply_group_config(pool, chat_id, cfg)` validates-then-writes in
  one transaction (DELETE + INSERT blocked/limits/whitelist, UPDATE
  groups.notify_enabled). Stats untouched.
- Private flow: `export:{chat_id}` → owner check → send line as
  code-formatted message + hint. `import:{chat_id}` → owner check → arm pending,
  send prompt. `route_private` checks pending-import BEFORE pending-limit;
  on consume: re-check `get_owner == from_id` else deny+clear; decode fails →
  send bad-value msg, KEEP pending for retry; success → apply, clear pending,
  send ok + re-render hint. `/start` clears both pendings.
- Keyboards: add Export/Import rows to `group_menu_kb`, new prefixes
  `export:{chat_id}` `import:{chat_id}` in `route_cb`, docstring update.
- Texts (EN msgid + RU in `i18n_ru.py`): export title/hint, import prompt,
  import ok, import bad value.

## Left to builder
- Exact button order/labels and whether export message also shows a summary.
- Whether bad import keeps pending (recommended: keep) vs clears after N fails.
- Exact 500-user cap and max line length guard before DB write.
