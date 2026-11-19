# Cooldown Countdown — short design (2026-11-19)

## Intent / why
Cooldown deletes confuse users: they see "Slow down" but not how long to wait, so they retry and get deleted again. Show remaining time in the notice: e.g. "Phrase. Please wait another 10 seconds."

## Goals
- Cooldown notices (only) append remaining time: `{phrase} Please wait another {n} second(s).`
- Remaining = `ceil(cooldown_sec - elapsed_sec)`, min 1, never 0.
- EN + RU via existing `n()` plural helper; RU forms in `RU_PLURALS`.
- Blocked/duration notices unchanged (no suffix).
- Unique-notice dedup still applies to full text including suffix.

## Non-goals / anti-goals
- No change to duration caps, blocked types, whitelist, or cooldown windows themselves.
- No persistent cooldown state (still in-memory `dict[(chat, user, type)]`, restart resets — accepted in 2026-10-30 design).
- No `format_window()` style (`30s`/`1m`); raw seconds per request example.
- No extra group spam; suffix rides on existing `get_notify` notice path.

## Constraints
- `handlers_group._handle` is where `now`, `last`, `cool` meet; `adapters.message_fields` untouched.
- `notices.render_notice(user, ctype, reason, rng)` is the single render entry; `render_unique_notice` wraps it for dedup.
- `tests/test_i18n.py::test_all_literal_msgids_covered` requires every literal passed to `_()`/`n()` to exist in `i18n_ru.py` (`RU_STRINGS` / `RU_PLURALS`).
- Existing tests assert `render_unique_notice` call args (`test_group_limits.py`, `test_group.py`) — update them.

## Approaches
- **A — Humanized window (`format_window`)**: "wait another 1m". Rejected: coarse, doesn't tick down, mismatches requested "10 seconds".
- **B — Raw ceil seconds suffix (picked)**: exact, trivial, matches example. `ceil` avoids "0 seconds" flicker when 0.2s left.
- **C — Separate countdown message**: extra group noise. Rejected (anti-goal: silent + single notice).

## How (picked B)
- **limits.py**: `remaining_cooldown_sec(now, last, cooldown_sec) -> int | None`: None if no cooldown/expired/no last; else `max(1, ceil(cool - elapsed))`.
- **notices.py**: `render_notice(..., remaining_sec: int | None = None)`, same for `render_unique_notice`; if `reason == "cooldown"` and `remaining_sec is not None`: `base + " " + n("Please wait another {n} second.", "Please wait another {n} seconds.", remaining).format(n=remaining)`. `n()` auto-selects RU forms when `get_lang()=="ru"`.
- **i18n_ru.py**: `RU_PLURALS[("Please wait another {n} second.", "Please wait another {n} seconds.")] = ("Подождите ещё {n} секунду.", "Подождите ещё {n} секунды.", "Подождите ещё {n} секунд.")`.
- **handlers_group.py**: in cooldown-fail branch compute `remaining` via helper; thread `remaining_sec` through `_remove(pool, app, msg, fields, chat_id, ctype, reason, remaining_sec=None)` → `_send_notice(..., remaining_sec)` → `render_unique_notice(..., remaining_sec=...)`. Blocked/duration pass `None`.
- **Tests**: pure helper (expired/exact/ceil/min-1/None cases); render EN singular/plural + RU plural + no-suffix for blocked/duration + suffix survives unique-retry; handler passes correct remaining (e.g. 30s window, 10s elapsed → 20).

## Left to builder
- Exact RU wording (proposal above); exact EN msgids (proposal above).
- Whether to clamp huge windows (e.g. 1d → "wait another 86399 seconds") or humanize above 120s — proposal: keep raw seconds in v1, revisit if noisy.
