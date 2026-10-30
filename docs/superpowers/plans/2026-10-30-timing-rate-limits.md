# Timing + Rate Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Per-chat per-type max-duration caps and 1-per-window cooldowns enforced with AND, configured via `30s`-style input.

**Architecture:** New `limits.py` holds pure parsing/decision helpers; `db.py` stores only settings in a new `limits` table; `handlers_group.py` enforces with an in-memory `dict` for last-passed timestamps (approach B); private-chat UI adds Limits screens with pending text input.

**Tech Stack:** Python, asyncpg/Postgres, GoyGram event objects, pytest (asyncio_mode=auto).

**Spec:** `docs/superpowers/specs/2026-10-30-timing-rate-limits-design.md`

## Global Constraints
- AND inside limits: delete if duration exceeds OR cooldown violated; whitelist and `/command` exempt bypass both.
- Rate is always 1-per-window per user in chat; no burst counts.
- Cooldown state is in-memory only; restart clears windows.
- Suffix format `30s`, `1m`, `1h`, `1d` case-insensitive, plus `off`/`0`/empty to clear.
- Duration caps only for `voice`, `video`, `video_note`, `audio`, `animation`; cooldown applies to all `CONTENT_TYPES`.

## Review Focus
- Suffix parser receiving `5x`, `-1m`, `1.5h`, ` 1m `, `OFF` expects ValueError for garbage, seconds for valid, None for off variants.
- Voice dict as `{"duration": 65}` vs object with `.duration` vs missing duration expects cap skipped (None passes), not crash.
- Two users sending same type concurrently expect independent buckets (key includes user_id).
- Deleted (over-limit) message expects timestamp NOT updated, so a retry after window succeeds.
- Private-chat free text `hello` while no pending limit input expects ignored (no crash, no /start trigger).

---

### Task 1: Limits core helpers

**Files:**
- Create: `limits.py`
- Test: `tests/test_limits.py`

**Interfaces:**
- Consumes: `classify.CONTENT_TYPES`, Telegram `duration` int seconds (context7 `/websites/core_telegram_bots_api`).
- Produces: `limits.parse_window(s: str | None) -> int | None`, `limits.format_window(sec: int | None) -> str`, `limits.DURATION_TYPES: set[str]`, `limits.get_duration(fields) -> int | None`, `limits.is_duration_ok(dur: int | None, max_dur: int | None) -> bool`, `limits.is_cooldown_ok(now, last, cooldown_sec: int | None) -> bool`

- [ ] **Step 1: Write the failing test**

```python
def test_parse_window_suffixes():
    assert parse_window("30s") == 30
    assert parse_window("1m") == 60
    assert parse_window("2h") == 7200
    assert parse_window("1d") == 86400
    assert parse_window("off") is None
    assert parse_window("0") is None
    assert parse_window("") is None

def test_parse_window_rejects_garbage():
    import pytest
    for bad in ["5x", "-1m", "1.5h", "hello"]:
        with pytest.raises(ValueError):
            parse_window(bad)

def test_get_duration_kinds():
    from types import SimpleNamespace
    assert get_duration(SimpleNamespace(voice={"duration": 65}, video=None, video_note=None, audio=None, animation=None)) == 65
    assert get_duration(SimpleNamespace(voice=None, video=None, video_note=None, audio=None, animation=None)) is None

def test_decision_helpers():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    assert is_duration_ok(61, 60) is False
    assert is_duration_ok(None, 60) is True
    assert is_duration_ok(10, None) is True
    assert is_cooldown_ok(now, now - timedelta(seconds=31), 30) is True
    assert is_cooldown_ok(now, now - timedelta(seconds=10), 30) is False
    assert is_cooldown_ok(now, None, 30) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_limits.py -v`
Expected: FAIL with "No module named 'limits'" / function not defined

- [ ] **Step 3: Implement `parse_window`, `format_window`, `get_duration`, `is_duration_ok`, `is_cooldown_ok` in `limits.py`**

Regex `^\s*(\d+)\s*([smhdSMHD])\s*$`, multipliers s=1 m=60 h=3600 d=86400; `off`/`0`/empty/None -> None; else ValueError. `get_duration` checks `voice/video/video_note/audio/animation` attrs in order, supports dict `.get("duration")` or object `.duration`, coerces int, returns None if missing.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_limits.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add limits.py tests/test_limits.py
git commit -m "feat: add limits parsing and decision helpers"
```

### Task 2: Limits settings storage

**Files:**
- Modify: `db.py`
- Test: `tests/test_db.py` (extend, unit for pure parts stays; DB CRUD covered by new integration-style test with fake pool in `tests/test_limits_db.py` or mocked asyncpg)

**Interfaces:**
- Consumes: `limits.py` seconds ints.
- Produces: `db.get_limits(pool, chat_id: int) -> dict[str, tuple[int|None, int|None]]`, `db.get_limit(pool, chat_id: int, ctype: str) -> tuple[int|None, int|None]`, `db.set_limit(pool, chat_id: int, ctype: str, max_duration_sec: int|None, cooldown_sec: int|None) -> None`, `db.clear_limit(pool, chat_id: int, ctype: str) -> None`; `SCHEMA` includes `limits` table; `reset_group_data` clears limits.

- [ ] **Step 1: Write the failing test**

```python
async def test_set_get_clear_limit():
    pool = FakePool()
    await set_limit(pool, -1001, "voice", 60, 30)
    assert await get_limit(pool, -1001, "voice") == (60, 30)
    await clear_limit(pool, -1001, "voice")
    assert await get_limit(pool, -1001, "voice") == (None, None)
```

(FakePool mimics `pool.acquire()` returning conn with `execute/fetchrow/fetch` backed by dict; mirror existing `test_db.py` mock style — no live DB.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_limits_db.py -v`
Expected: FAIL with "cannot import name 'set_limit'"

- [ ] **Step 3: Implement `limits` table + helpers in `db.py`**

`SCHEMA` += `CREATE TABLE IF NOT EXISTS limits (chat_id BIGINT NOT NULL, ctype TEXT NOT NULL, max_duration_sec INTEGER, cooldown_sec INTEGER, PRIMARY KEY (chat_id, ctype));`. `set_limit` uses `INSERT ... ON CONFLICT (chat_id, ctype) DO UPDATE`. `get_limit` returns `(None,None)` when missing. Extend `reset_group_data` and `register_group` fresh_start path to `DELETE FROM limits WHERE chat_id=$1`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_limits_db.py tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_limits_db.py
git commit -m "feat: store per-type duration and cooldown limits"
```

### Task 3: Group enforcement with in-memory cooldowns

**Files:**
- Modify: `handlers_group.py`
- Test: `tests/test_group.py` (extend) + `tests/test_group_limits.py`

**Interfaces:**
- Consumes: `limits.get_duration/is_duration_ok/is_cooldown_ok`, `db.get_limit` (single-type lookup to keep per-message queries minimal).
- Produces: `handlers_group._cooldown_last: dict[tuple[int,int,str], datetime]`, extended `_handle` behavior (no signature change).

- [ ] **Step 1: Write the failing test**

```python
async def test_voice_over_duration_deleted():
    msg = GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}}))
    with (patch("handlers_group.get_blocked", AsyncMock(return_value=set())), patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)), patch("handlers_group.get_notify", AsyncMock(return_value=False)), patch("handlers_group.incr_stat", AsyncMock()) as incr, patch("handlers_group.get_limit", AsyncMock(return_value=(60, None))), patch("handlers_group._cooldown_last", {})):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_called_once()
    incr.assert_called_once()

async def test_cooldown_second_send_deleted_first_passes():
    # first passes and records timestamp, second within 30s deleted and does not extend window
    # third user with different user_id passes (independent buckets)

async def test_cooldown_buckets_are_per_user():
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_limits.py -v`
Expected: FAIL (get_limit missing / delete not called)

- [ ] **Step 3: Implement enforcement in `handlers_group.py`**

After whitelist/command/blocked checks and before delete: `ctype = classify(fields)`; `max_dur, cool = await get_limit(pool, chat_id, ctype)`; `dur = get_duration(fields)`; if not `is_duration_ok` -> delete+stat path (shared with blocked); elif not `is_cooldown_ok(now, _cooldown_last.get((chat_id,user_id,ctype)), cool)` -> delete+stat without updating; else update `_cooldown_last[key]=now` and continue (no delete). Whitelist/command/own-message early returns unchanged. On delete failure (BadRequest) keep existing `_notify_no_rights` path.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_group.py tests/test_group_limits.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add handlers_group.py tests/test_group_limits.py
git commit -m "feat: enforce duration caps and per-user cooldowns"
```

### Task 4: Private-chat Limits UI + copy

**Files:**
- Modify: `keyboards.py`, `handlers_private.py`, `texts.py`, `i18n_ru.py`
- Test: `tests/test_private.py` (extend) + `tests/test_keyboards.py` (extend)

**Interfaces:**
- Consumes: `db.get_limits/get_limit/set_limit/clear_limit`, `limits.parse_window/format_window/DURATION_TYPES`, `classify.CONTENT_TYPES`.
- Produces: `keyboards.limits_list_kb(chat_id, limits: dict)`, `keyboards.limit_detail_kb(chat_id, ctype, dur, cool)`; callbacks `limits:{chat}`, `lim:{chat}:{ctype}`, `lim_dur:{chat}:{ctype}`, `lim_cool:{chat}:{ctype}`, `lim_clear:{chat}:{ctype}`; `handlers_private._pending_limits: dict[int, tuple[int,str,str]]`; `texts.LIMITS_*` prompts.

- [ ] **Step 1: Write the failing test**

```python
async def test_limits_list_renders():
    cb = GCb("limits:-1001", 111)
    with (patch owner 111, patch get_limits return {"voice": (60, 30)}):
        await on_limits_list(pool, app, cb)
    assert app.edit_msg.await_count == 1

async def test_limit_value_parse_error_keeps_pending():
    # send "5x" as pending duration value -> error reply, pending kept
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_private.py::test_limits_list_renders -v`
Expected: FAIL with "no function on_limits_list"

- [ ] **Step 3: Implement keyboards + handlers + copy**

`group_menu_kb` adds `Limits` row (`limits:{chat}`). List screen shows per-type `ctype · dur/cool` via `format_window`. Detail screen shows current values + Set-cooldown always, Set-duration only if ctype in `DURATION_TYPES`, + Clear. Tapping dur/cool sets `_pending_limits[owner_id]=(chat,ctype,field)` and asks "Send max duration as 30s/1m/1h/1d or off". `route_private` checks pending before `/start`: parse with `parse_window`, on ValueError reply error and keep pending, on success `set_limit` + clear pending + confirm. `route_cb` routes new prefixes. `texts.py` adds `LIMITS_TITLE`, `LIMIT_PROMPT_DUR`, `LIMIT_PROMPT_COOL`, `LIMIT_SET_OK`, `LIMIT_BAD_VALUE`, `LIMITS_BUTTON`; `i18n_ru.py` adds RU equivalents. Also update `render_group_menu` callers to pass through (no signature break: `group_menu_kb` gains optional param or new row unconditional).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_private.py tests/test_keyboards.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add keyboards.py handlers_private.py texts.py i18n_ru.py tests/test_private.py
git commit -m "feat: add Limits config UI with exact-value input"
```

### Task 5: Wiring + full verification

**Files:**
- Modify: `db.py` (reset path if missed), `handlers_private.py` (router edge), docs
- Test: full suite

**Interfaces:**
- Consumes: all Tasks 1-4 outputs.
- Produces: working feature, no regressions.

- [ ] **Step 1: Write the failing test**

```python
async def test_private_router_ignores_pending_text_in_group():
    # group chat text with pending entry for owner does not trigger limit-set
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_private.py -k pending -v`
Expected: FAIL or missing behavior

- [ ] **Step 3: Implement router guard + `reset_group_data` limits cleanup if missed**

`route_private` only honors `_pending_limits` when `chat_type == "private"`; `/start` clears pending for that owner.

- [ ] **Step 4: Run full unit suite**

Run: `python -m pytest tests/ -m "not integration" -q`
Expected: PASS, zero failures

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: wire limits pending input and cleanup"
```
