# Timing + Rate Limits — short design (2026-10-30)

## Intent / why
Owners want more than on/off blocks: cap media length (e.g. voice/video not longer
than `1m`) and per-user frequency (e.g. `30s` = 1 message per 30s, per user in
that chat). Requested examples: 1 text/min, voices max `1m` with cooldown.

## Goals
- Per-chat, per-type settings: `max_duration_sec` (media length cap) + `cooldown_sec`
  (1-per-window per user).
- AND inside limits: message passes only if duration OK **and** cooldown OK;
  either failure -> delete (same silent delete + `incr_stat` as blocked).
- Per-user-in-chat buckets; whitelist + `/command` exempt bypass both checks.
- Exact suffix input: `30s`, `1m`, `1h`, `1d` (case-insensitive), plus `off`/`0` to clear.
- Applies to duration types (`voice`, `video`, `video_note`, `audio`, `animation`);
  all `CONTENT_TYPES` in `classify.py` get cooldown, only duration types get duration cap.

## Non-goals / anti-goals
- No burst counts (dropped `2/1h` idea — always 1 per window).
- No chat-global flood control, no per-thread/topic splits.
- No persistent rate history (approach B): restart resets cooldowns.
- No Telegram native slow-mode use; no extra notice spam to group.

## Constraints
- Current flow: `handlers_group._handle` is stateless; `adapters.message_fields`
  only passes presence, not `duration`. `keyboards`/`handlers_private` have no
  free-text input today (`route_private` only handles `users_shared` + `/start`).
- Telegram Bot API: `duration` int seconds on voice/video/video_note/audio/animation
  (`/websites/core_telegram_bots_api` via context7). Goygram: `msg.get("voice")`
  lazy lookup returns that dict; add extractor, no new dep.
- Postgres already used per message (`get_blocked`, `is_whitelisted`); settings
  belong there, cooldowns stay in memory like `_last_notify`.

## Approaches
- **A — DB settings + DB cooldown state.** Survives restart, extra writes per message.
  Rejected by owner (heavier than needed).
- **B — DB settings + in-memory cooldowns (picked).** `limits` table for settings,
  `dict[(chat_id,user_id,ctype)] -> datetime` for last-passed timestamps.
  Simple, matches `_last_notify` pattern; restart clears windows (accepted).
- Native slow-mode rejected: chat-wide only, not per-type/per-user.

## How (picked B)
- **DB:** `CREATE TABLE limits(chat_id BIGINT, ctype TEXT, max_duration_sec INT NULL,
  cooldown_sec INT NULL, PRIMARY KEY(chat_id,ctype))`; helpers
  `get_limits(chat_id)`, `set_limit(chat_id,ctype,duration,cooldown)`.
  `reset_group_data` also clears limits.
- **Parse:** `parse_window(s) -> int|None`: regex `^(\d+)(s|m|h|d)$`, `off`/`0`/empty
  -> None; store seconds. Same parser for duration cap and cooldown window.
- **Adapters:** `get_duration(fields) -> int|None`: read nested
  `voice/video/video_note/audio/animation` dict-or-obj `.get("duration")`.
- **Enforce (`handlers_group._handle`):** after whitelist/command/blocked checks,
  if `ctype` has limits: duration fail if `dur is not None and dur > max_dur`;
  cooldown fail if `now - last < cooldown`; delete on either fail (don't update
  timestamp); on pass update `last` to `now` then continue. Whitelist bypasses.
- **Config UI:** `group_menu_kb` += `Limits` button (`limits:{chat}`); list screen
  per type shows `dur/cool` summary; tap -> detail with `Set duration` /
  `Set cooldown` / `Clear` callbacks; next private text message is taken as value
  via pending-input dict `(owner_id -> (chat_id,ctype,field))` in `route_private`.
- **Copy/i18n:** new `texts.py` prompts + errors; RU in `i18n_ru.py`; fallback EN.
- **Tests:** parser unit, duration extractor, pure cooldown/duration decision,
  group-handler fake app/pool for AND + whitelist bypass, limits CRUD.

## Left to builder
- Exact button labels/wording; max input guard (e.g. cap `365d`); whether
  limit-deletes reuse `get_notify` notices (proposal: silent, same as blocks).
- Pending-input timeout/cancel (`/start` cancels?) — builder call, keep simple.
