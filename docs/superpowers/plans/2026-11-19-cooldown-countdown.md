# Cooldown Countdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append "Please wait another N seconds." to cooldown notices with ceil remaining time.

**Architecture:** Pure `limits.py` helper computes `ceil(cool - elapsed)`; `notices.py` appends a pluralized suffix only for `reason=="cooldown"`; `handlers_group.py` threads the value from the fail branch to the renderer.

**Tech Stack:** Python, `math.ceil`, existing `i18n.n()` / `RU_PLURALS`, in-memory `_cooldown_last`, pytest + AsyncMock fakes.

**Spec:** `docs/superpowers/specs/2026-11-19-cooldown-countdown-design.md`

## Global Constraints

- Cooldowns stay in-memory `dict[(chat_id, user_id, ctype)] -> datetime`; restart resets windows.
- Delete-then-notify path unchanged: `delete_msg` + `incr_stat`, notice only if `get_notify(chat_id)` is true.
- English msgids with RU fallback: every literal to `_()`/`n()` must exist in `i18n_ru.py` (`RU_STRINGS` / `RU_PLURALS`) — enforced by `tests/test_i18n.py::test_all_literal_msgids_covered`.
- Cooldown buckets are per-(chat, user, type); duration fails neither read nor write cooldown state.
- Anonymous (`sender_id is None`) bypasses cooldown but still gets blocked/duration checks.

## Review Focus

- `cooldown_sec=3600+` shows huge seconds (e.g. 86399) — reasonable person expects raw seconds in v1 per spec; humanizing is a follow-up.
- `elapsed=29.9s` of `30s` must show `1`, never `0` — ceil + `max(1, ...)` pins it.
- `elapsed >= cooldown` exactly at boundary passes (no delete, no notice) — no suffix on pass path.
- RU plural 1/2-4/5+ (1 секунду, 3 секунды, 5 секунд) selects correct form via `n()`.
- `render_unique_notice` dedup compares full text including suffix — two consecutive cooldowns with different remaining are not dupes.

---

### Task 1: Remaining-seconds helper in `limits.py`

**Files:**
- Modify: `limits.py`
- Test: `tests/test_limits.py`

**Interfaces:**
- Consumes: existing `is_cooldown_ok(now: datetime, last: datetime | None, cooldown_sec: int | None) -> bool`
- Produces: `remaining_cooldown_sec(now: datetime, last: datetime | None, cooldown_sec: int | None) -> int | None` — `None` if no wait needed (`cooldown_sec is None` or `last is None` or `elapsed >= cooldown_sec`); else `max(1, ceil(cooldown_sec - elapsed))` where `elapsed = (now - last).total_seconds()`.

- [ ] **Step 1: Write the failing test**

```python
def test_remaining_cooldown_sec():
    from datetime import datetime, timedelta, timezone
    from limits import remaining_cooldown_sec
    now = datetime.now(timezone.utc)
    assert remaining_cooldown_sec(now, None, 30) is None
    assert remaining_cooldown_sec(now, now - timedelta(seconds=40), 30) is None
    assert remaining_cooldown_sec(now, now - timedelta(seconds=30), 30) is None
    assert remaining_cooldown_sec(now, now - timedelta(seconds=10), 30) == 20
    assert remaining_cooldown_sec(now, now - timedelta(milliseconds=29900), 30) == 1
    assert remaining_cooldown_sec(now, now, None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_limits.py::test_remaining_cooldown_sec -v`
Expected: FAIL with "cannot import name 'remaining_cooldown_sec'"

- [ ] **Step 3: Implement `remaining_cooldown_sec(now, last, cooldown_sec) -> int | None` in `limits.py`**

Use `math.ceil`; return `None` on the no-wait cases above, else `max(1, ceil(...))`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_limits.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add limits.py tests/test_limits.py
git commit -m "feat: add remaining_cooldown_sec helper"
```

---

### Task 2: Suffix rendering in `notices.py` + RU strings

**Files:**
- Modify: `notices.py`, `i18n_ru.py`
- Test: `tests/test_notices.py`, `tests/test_i18n.py` (coverage, no edit needed — must stay green)

**Interfaces:**
- Consumes: `remaining_cooldown_sec` result (plain `int | None`); `i18n.n(singular, plural, num)` + `i18n.get_lang()`
- Produces: `render_notice(user: str, ctype: str, reason: str | None = None, rng=random.choice, remaining_sec: int | None = None) -> str` and `render_unique_notice(user: str, ctype: str, previous: list[str], reason: str | None = None, rng=random.choice, remaining_sec: int | None = None) -> str` — when `reason == "cooldown"` and `remaining_sec is not None`, return `f"{base} {suffix}"` where `suffix = n("Please wait another {n} second.", "Please wait another {n} seconds.", remaining_sec).format(n=remaining_sec)`; otherwise return `base` unchanged. RU suffix resolves via `RU_PLURALS` entry below.

- [ ] **Step 1: Write the failing tests**

```python
def test_cooldown_suffix_en_singular_plural():
    from i18n import set_lang
    from notices import render_notice
    set_lang("en")
    try:
        one = render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0], remaining_sec=1)
        assert one.endswith("Please wait another 1 second.")
        ten = render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0], remaining_sec=10)
        assert ten.endswith("Please wait another 10 seconds.")
    finally:
        set_lang("en")

def test_cooldown_suffix_ru_plural_forms():
    from i18n import set_lang
    from notices import render_notice
    set_lang("ru")
    try:
        assert render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0], remaining_sec=1).endswith("Подождите ещё 1 секунду.")
        assert render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0], remaining_sec=3).endswith("Подождите ещё 3 секунды.")
        assert render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0], remaining_sec=5).endswith("Подождите ещё 5 секунд.")
    finally:
        set_lang("en")

def test_no_suffix_without_remaining_or_non_cooldown():
    from notices import render_notice
    base_cool = render_notice("@bob", "text", reason="cooldown", rng=lambda s: s[0])
    assert "Please wait another" not in base_cool
    base_blocked = render_notice("@bob", "text", reason="blocked", rng=lambda s: s[0], remaining_sec=10)
    assert "Please wait another" not in base_blocked and "Подождите" not in base_blocked

def test_unique_notice_keeps_suffix_and_dedups_on_full_text():
    from notices import NOTICE_TEMPLATES, render_unique_notice
    rng_calls = iter([NOTICE_TEMPLATES[0], "jerk", NOTICE_TEMPLATES[0], "jerk", NOTICE_TEMPLATES[1], "jerk"])
    dupe_base = NOTICE_TEMPLATES[0].format(user="@bob", insult="jerk", type="text message")
    dupe = f"{dupe_base} Please wait another 20 seconds."
    fresh_base = NOTICE_TEMPLATES[1].format(user="@bob", insult="jerk", type="text message")
    fresh = f"{fresh_base} Please wait another 20 seconds."
    assert render_unique_notice("@bob", "text", [dupe], reason="cooldown", rng=lambda s: next(rng_calls), remaining_sec=20) == fresh
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notices.py -v -k "suffix or no_suffix"`
Expected: FAIL (unexpected keyword `remaining_sec`, missing RU forms)

- [ ] **Step 3: Implement suffix in `notices.py` + RU entry in `i18n_ru.py`**

In `i18n_ru.py` add to `RU_PLURALS`: `('Please wait another {n} second.', 'Please wait another {n} seconds.'): ('Подождите ещё {n} секунду.', 'Подождите ещё {n} секунды.', 'Подождите ещё {n} секунд.')`. In `notices.py` import `n`, add `remaining_sec` kwargs, append suffix only on the cooldown branch (both EN template path and RU reply path share the same suffix step after base is chosen).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_notices.py tests/test_i18n.py -v`
Expected: PASS (including `test_all_literal_msgids_covered`)

- [ ] **Step 5: Commit**

```bash
git add notices.py i18n_ru.py tests/test_notices.py
git commit -m "feat: append cooldown countdown suffix to notices"
```

---

### Task 3: Thread remaining through `handlers_group.py`

**Files:**
- Modify: `handlers_group.py`
- Test: `tests/test_group_limits.py`, `tests/test_group.py`

**Interfaces:**
- Consumes: `remaining_cooldown_sec` from Task 1; `render_unique_notice(..., remaining_sec)` from Task 2
- Produces: `_remove(pool, app, msg, fields, chat_id: int, ctype: str, reason: str, remaining_sec: int | None = None) -> None`; `_send_notice(pool, app, chat_id: int, user: str, ctype: str, reason: str, remaining_sec: int | None = None) -> None`; `_handle` cooldown-fail branch computes `remaining = remaining_cooldown_sec(now, _cooldown_last.get(key), cool)` and passes it; blocked/duration branches pass `None`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_cooldown_fail_passes_remaining_to_notice():
    from datetime import datetime, timedelta, timezone
    from unittest.mock import AsyncMock, patch
    from handlers_group import handle_group_message
    from test_group import GMsg, make_app, make_msg, sender
    now = datetime.now(timezone.utc)
    store = {(-1001, 111, "text"): now - timedelta(seconds=10)}
    patches = dict(
        get_blocked=AsyncMock(return_value=set()),
        is_whitelisted=AsyncMock(return_value=False),
        incr_stat=AsyncMock(),
        get_notify=AsyncMock(return_value=True),
        get_owner=AsyncMock(return_value=111),
        get_owner_lang=AsyncMock(return_value="en"),
        get_limit=AsyncMock(return_value=(None, 30)),
    )
    from contextlib import ExitStack
    stack = ExitStack()
    for name in ("get_blocked", "is_whitelisted", "incr_stat", "get_notify", "get_owner", "get_owner_lang", "get_limit"):
        stack.enter_context(patch(f"handlers_group.{name}", patches[name]))
    with stack, patch("handlers_group._cooldown_last", store), patch("handlers_group._recent_notice_texts", {}), patch("handlers_group.render_unique_notice", return_value="N") as ru, patch("handlers_group._now", return_value=now):
        await handle_group_message(pool := object(), app := make_app(), GMsg(make_msg(**{"from": sender(), "text": "again"})), 777)
    ru.assert_called_once_with("@bob", "text", [], reason="cooldown", remaining_sec=20)
```

Plus update existing assertions: `test_duration_fail_notice_uses_duration_reason` expects `render_unique_notice("@bob", "voice", [], reason="duration", remaining_sec=None)`; `test_cooldown_fail_notice_uses_cooldown_reason` second call expects `remaining_sec=30`; `test_new_notice_avoids_previous_replies` expects `reason="blocked", remaining_sec=None`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_group_limits.py tests/test_group.py -v`
Expected: FAIL (missing `remaining_sec` kwarg / wrong value)

- [ ] **Step 3: Implement threading in `handlers_group.py`**

Import `remaining_cooldown_sec`; in `_handle` cooldown branch compute it before `_remove`; extend `_remove` and `_send_notice` signatures with `remaining_sec: int | None = None` and forward to `render_unique_notice`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_group_limits.py tests/test_group.py tests/test_limits.py tests/test_notices.py tests/test_i18n.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add handlers_group.py tests/test_group_limits.py tests/test_group.py
git commit -m "feat: show cooldown countdown in restriction notice"
```
