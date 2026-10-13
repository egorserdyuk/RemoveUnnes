# Telegram Media Remover Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polling aiogram bot that silently deletes per-group blocked content types from non-whitelisted senders and exposes per-group config plus private stats to the owning user.

**Architecture:** Single async polling process. Pure `classify()` decides one content-type per message; thin `asyncpg` DB layer holds per-group blocked sets, whitelist, and counters; three routers (private, group, membership) plus inline/reply keyboard builders. No FSM, no webhooks.

**Tech Stack:** Python 3.11+, `aiogram==3.31.0`, `asyncpg`, `pytest`, PostgreSQL 15+, `docker compose` for local DB.

**Spec:** `docs/superpowers/specs/2026-10-13-telegram-cleaner-design.md`

## Global Constraints

- `aiogram==3.31.0` pinned — use v3 `Router`, `F.*` magic filters, `InlineKeyboardBuilder` / `ReplyKeyboardBuilder`, `my_chat_member` events.
- Env: `BOT_TOKEN` (required), `POSTGRES_DSN` (e.g. `postgresql://user:pass@localhost:5432/remover`).
- Polling only; `allowed_updates` must include `message, edited_message, my_chat_member, callback_query`.
- Default = everything allowed (empty `blocked` table means allow); service messages are NEVER deleted.
- All bot UI copy in English.
- Group handler is catch-all bare `@router.message()` + manual `classify()` — not dozens of `F.*` handlers.
- Whitelist is per-group, unlimited; `request_users` picker with `user_is_bot=False, max_quantity=10`, repeatable.
- Stats visible only in private chat to the group owner, on demand; group deletions are silent.

## Review Focus

- Anonymous admin / channel post (`from_user is None`, `sender_chat` set) with blocked type — expect deleted by type, never whitelist-bypassed.
- Photo/video with caption when `photo` blocked but `text` allowed — expect deleted as `photo`, caption does not save it.
- `/command@otherbot args` when `text` blocked — expect allowed (bot_command entity at offset 0 exempts).
- Edited message changing allowed text into blocked media/caption — expect re-checked and deleted via `edited_message` path.
- Non-owner tapping another owner's group button — expect "Only the person who added me here can change this." and zero state change.

---

### Task 1: Scaffolding, config, texts, compose

**Files:**
- Create: `config.py`
- Create: `texts.py`
- Create: `docker-compose.yml`
- Create: `requirements.txt` (modify existing: add `asyncpg`, `pytest`, `pytest-asyncio`)
- Create: `README.md`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: none (first task).
- Produces:
  - `config.Settings(token: str, dsn: str)` / `config.load() -> Settings` (reads `BOT_TOKEN`, `POSTGRES_DSN`, raises `RuntimeError` if missing).
  - `texts.*: str` constants used by later tasks: `START, GROUPS_EMPTY, GROUP_TITLE, NEED_ADMIN, NOT_OWNER, CONNECTED, STATS_EMPTY`.
  - `docker-compose.yml` service `db` (postgres:15, port 5432, volume, password from env).

- [ ] **Step 1: Write the failing test**

```python
def test_load_missing_env_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        load()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_load_missing_env_raises -v`
Expected: FAIL with "load not defined" / collection error.

- [ ] **Step 3: Implement `load() -> Settings` in `config.py`, texts in `texts.py`, compose + requirements + README (privacy-OFF + admin-rights notes)**

Exact English copy from spec: START mentions adding bot as admin with Delete rights; NOT_OWNER = "Only the person who added me here can change this."; NEED_ADMIN mentions needing admin + delete rights.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py texts.py docker-compose.yml requirements.txt README.md tests/test_config.py
git commit -m "feat: add config, texts, compose scaffolding"
```

---

### Task 2: Content-type classifier (pure, no Telegram network)

**Files:**
- Create: `classify.py`
- Test: `tests/test_classify.py`

**Interfaces:**
- Consumes: `aiogram.types.Message` (duck-typed in tests via `SimpleNamespace`).
- Produces:
  - `CONTENT_TYPES: list[str]` = `["story_forward","photo","video","video_note","voice","audio","document","animation","sticker","poll","contact","location","venue","dice","game","invoice","successful_payment","checklist","text"]` (priority order, `text` last).
  - `classify(message) -> str | None` — returns one ctype or `None` for service/unknown (service = any `new_chat_members, left_chat_member, pinned_message, chat_shared, users_shared, new_chat_title`, etc.).
  - `is_command_exempt(message) -> bool` — True when `message.text` starts with `/` and entities contain `bot_command` at offset 0.

- [ ] **Step 1: Write the failing tests**

```python
def test captioned_photo_counts_as_photo(): ...
def test command_exempt_when_text_blocked(): ...
def test service_message_returns_none(): ...
def test anonymous_channel_photo_classifies(): ...
def test edited_caption_media_still_media(): ...
```

Concrete: captioned photo fixture (`photo=[...], caption="hi"`) → `classify() == "photo"`; command fixture (`text="/start@otherbot", entities=[{type:"bot_command",offset:0}]`) → `is_command_exempt() is True`; service fixture (`new_chat_members=[...]`) → `None`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_classify.py -v`
Expected: FAIL (module/function missing).

- [ ] **Step 3: Implement `CONTENT_TYPES`, `classify()`, `is_command_exempt()` in `classify.py`**

Priority order exactly as listed (text last). Check fields in order; return first present. `story_forward` via `getattr(message, "story", None)`.

- [ ] **Step 4: Run tests to verify they pass (pins 2 Review Focus lines: caption-vs-text, /command exemption)**

Run: `pytest tests/test_classify.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add classify.py tests/test_classify.py
git commit -m "feat: add message content-type classifier"
```

---

### Task 3: PostgreSQL layer + moderation decision helpers

**Files:**
- Create: `db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `config.Settings`; `classify.CONTENT_TYPES`.
- Produces:
  - `async def init_pool(dsn: str) -> asyncpg.Pool`
  - `async def init_schema(pool) -> None` (`CREATE TABLE IF NOT EXISTS owners, groups, blocked, whitelist, stats, pending_greetings, notify_state`).
  - `async def register_group(pool, chat_id: int, owner_id: int, title: str) -> str` returns `"created" | "kept" | "fresh_start"` (same owner re-add keeps; different owner wipes blocked/whitelist/stats and takes over).
  - `async def get_blocked(pool, chat_id: int) -> set[str]`
  - `async def toggle_blocked(pool, chat_id: int, ctype: str) -> set[str]`
  - `async def is_whitelisted(pool, chat_id: int, user_id: int) -> bool`
  - `async def add_whitelist(pool, chat_id: int, rows: list[tuple[int,str|None,str|None]]) -> None`
  - `async def remove_whitelist(pool, chat_id: int, user_id: int) -> None`
  - `async def incr_stat(pool, chat_id: int, ctype: str) -> None`
  - `async def get_stats(pool, chat_id: int) -> dict[str,int]`
  - `async def reset_stats(pool, chat_id: int) -> None`
  - `async def reset_group_data(pool, chat_id: int) -> None` (wipes blocked/whitelist/stats, keeps groups row).
  - `def should_delete(*, ctype: str | None, from_user_id: int | None, is_bot_self: bool, blocked: set[str], whitelisted: bool, command_exempt: bool) -> bool` (pure; False when ctype None/self/command-exempt/whitelisted/not-blocked; True otherwise — anonymous `from_user_id None` + non-whitelisted falls through to type check).
  - `def format_stats(stats: dict[str,int]) -> str` → `"removed messages: 1 photo; 2 videos"` or `"nothing removed yet"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_should_delete_anonymous_by_type():
    assert should_delete(ctype="photo", from_user_id=None, is_bot_self=False, blocked={"photo"}, whitelisted=False, command_exempt=False) is True

def test_should_delete_whitelisted_bypass(): ...
def test_should_delete_command_exempt(): ...
def test_format_stats_order_and_empty(): ...
def test_fresh_start_wipes(...): ...  # decision helper pure part or SQL string check if no live DB
```

DB integration tests marked `@pytest.mark.integration` and skipped without `POSTGRES_DSN_TEST`; unit tests run always.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v -m "not integration"`
Expected: FAIL (db module missing).

- [ ] **Step 3: Implement `db.py` with DDL + queries + pure `should_delete` / `format_stats`**

DDL per spec sketch; `blocked` absence = allowed; stats upsert `ON CONFLICT DO UPDATE SET cnt = stats.cnt + 1`.

- [ ] **Step 4: Run tests to verify they pass (pins anonymous-sender + stats-format Review lines)**

Run: `pytest tests/test_db.py -v -m "not integration"`
Expected: PASS. Optionally: `POSTGRES_DSN_TEST=... pytest tests/test_db.py -v -m integration`.

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add postgres layer and moderation decision helpers"
```

---

### Task 4: Keyboards + callback protocol

**Files:**
- Create: `keyboards.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: `classify.CONTENT_TYPES`; `db` row shapes.
- Produces:
  - Callback prefixes (exact): `group:{chat_id}`, `types:{chat_id}`, `toggle:{chat_id}:{ctype}`, `white:{chat_id}`, `unwhite:{chat_id}:{user_id}`, `stats:{chat_id}`, `reset_stats:{chat_id}`, `reset_group:{chat_id}`, `back_groups`, `noop`.
  - `groups_kb(groups: list[tuple[int,str]]) -> InlineKeyboardMarkup`
  - `group_menu_kb(chat_id: int, n_blocked: int, n_white: int) -> InlineKeyboardMarkup` (buttons: `Blocked types: N`, `Whitelist: N users`, `Stats`, `Reset stats`, `Remove group data`, `« My groups`).
  - `types_kb(chat_id: int, blocked: set[str]) -> InlineKeyboardMarkup` (one `✅/❌ {ctype}` button per type + `Back`).
  - `whitelist_kb(chat_id: int, users: list[tuple[int,str]]) -> InlineKeyboardMarkup` (per-user Remove + `Back`).
  - `picker_kb(request_id: int) -> ReplyKeyboardMarkup` (single `KeyboardButton(text="Pick users", request_users=KeyboardButtonRequestUsers(request_id=request_id, user_is_bot=False, max_quantity=10, request_name=True, request_username=True))`).

- [ ] **Step 1: Write the failing test**

```python
def test_types_kb_marks_blocked():
    kb = types_kb(-1001, {"photo"})
    flat = " ".join(b.text for row in kb.inline_keyboard for b in row)
    assert "✅ photo" in flat and "❌ video" in flat
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_keyboards.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement builders in `keyboards.py` with exact callback data above**

Use `InlineKeyboardBuilder` / `ReplyKeyboardBuilder` (aiogram 3.31 keyword-only constructors).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_keyboards.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add keyboards.py tests/test_keyboards.py
git commit -m "feat: add keyboards and callback protocol"
```

---

### Task 5: Private router (/start, groups, toggles, stats)

**Files:**
- Create: `handlers_private.py`
- Test: `tests/test_private.py`

**Interfaces:**
- Consumes: `config`, `db.*`, `keyboards.*`, `texts.*`.
- Produces: `router: Router` handling in private chat only (`F.chat.type == "private"`):
  - `Command("start")` → START text + groups list (flushes `pending_greetings` for this owner).
  - `F.data == "back_groups"` / `"my_groups"` → group list.
  - `F.data.startswith("group:")` → owner-gated group menu (non-owner → `NOT_OWNER` alert, no state change).
  - `F.data.startswith("toggle:")` → `toggle_blocked`, re-render types screen.
  - `F.data.startswith("stats:")` → `format_stats` output, owner-only.
  - `F.data.startswith("reset_stats:")`, `"reset_group:"` (confirm via second tap: `reset_group:{id}:confirm`) → DB ops.

- [ ] **Step 1: Write the failing tests (mock pool with AsyncMock; assert owner gate)**

```python
async def test_non_owner_tap_changes_nothing(): ...
async def test_toggle_roundtrip_updates_blocked(): ...
```

Verify: non-owner callback answers with NOT_OWNER and `toggle_blocked` never called; owner toggle calls DB and edits message.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_private.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `router` in `handlers_private.py` with owner checks on every callback**

Owner check helper: `async def _owner_only(pool, chat_id, user_id) -> bool`.

- [ ] **Step 4: Run tests to verify they pass (pins non-owner Review line)**

Run: `pytest tests/test_private.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers_private.py tests/test_private.py
git commit -m "feat: add private config router"
```

---

### Task 6: Membership router (add / re-add / kick, pending greetings)

**Files:**
- Create: `handlers_membership.py`
- Test: `tests/test_membership.py`

**Interfaces:**
- Consumes: `db.register_group`, `texts.CONNECTED`.
- Produces: `router: Router` on `my_chat_member`:
  - Bot becomes member/administrator → `register_group`; try DM owner CONNECTED; on `TelegramForbiddenError` insert `pending_greetings(owner_id, chat_id, title)`.
  - Bot left/kicked → mark inactive, keep settings (no wipe).
  - Helper `async def flush_pending(pool, bot, owner_id) -> None` called from `/start`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_readd_different_owner_fresh_start(): ...
async def test_dm_forbidden_queues_pending(): ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_membership.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement router + `flush_pending` with try/except `TelegramForbiddenError`**

Detect our bot via `event.new_chat_member.user.id == (await bot.me()).id`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_membership.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers_membership.py tests/test_membership.py
git commit -m "feat: add membership tracking with fresh-start transfer"
```

---

### Task 7: Whitelist picker flow (private only)

**Files:**
- Create: `handlers_whitelist.py` (or fold into private router — builder keeps separate for reviewability)
- Test: `tests/test_whitelist.py`

**Interfaces:**
- Consumes: `db.add_whitelist/remove_whitelist`, `keyboards.picker_kb/whitelist_kb`.
- Produces: `router: Router` (private only):
  - `F.data.startswith("white:")` → list + "Add via picker" (sends `picker_kb` with unique `request_id` per chat).
  - `F.data == "pick_users:{chat_id}"` → send ReplyKeyboard picker.
  - `F.users_shared` → resolve `users_shared.users[*].user_id`, `add_whitelist`, confirm count, remove ReplyKeyboard.
  - `F.data.startswith("unwhite:")` → owner-gated remove + re-render.

- [ ] **Step 1: Write the failing tests**

```python
async def test_users_shared_adds_all_ids(): ...
async def test_unwhite_requires_owner(): ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_whitelist.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement router; `request_id` = `chat_id & 0x7fffffff` rotating counter stored in-memory**

`user_is_bot=False`, `max_quantity=10`; repeatable for unlimited total.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_whitelist.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers_whitelist.py tests/test_whitelist.py
git commit -m "feat: add whitelist picker flow"
```

---

### Task 8: Group deletion handler + entrypoint

**Files:**
- Create: `handlers_group.py`
- Create: `bot.py`
- Test: `tests/test_group.py`

**Interfaces:**
- Consumes: `classify.*`, `db.{get_blocked,is_whitelisted,incr_stat}`, `texts.NEED_ADMIN`.
- Produces:
  - `router: Router` for `F.chat.type.in_({"group","supergroup"})` on `message` AND `edited_message`: skip self/service/`ctype None`/command-exempt/whitelisted/not-blocked; else `bot.delete_message` + `incr_stat`; on `TelegramBadRequest` → throttled owner DM (`notify_state`, max 1 per group per 10 min).
  - `bot.py: async def main() -> None` — `Bot(token, default=DefaultBotProperties(parse_mode=None))`, `Dispatcher`, `init_pool` + `init_schema`, `dp.include_routers(...)`, `await dp.start_polling(bot, allowed_updates=["message","edited_message","my_chat_member","callback_query"])`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_blocked_photo_deleted_and_counted(): ...
async def test_allowed_type_passes(): ...
async def test_no_rights_dms_owner_once(): ...
async def test_edited_message_rechecked(): ...
```

Mocks: fake `Bot.delete_message` (AsyncMock), fake pool returning blocked sets.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_group.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement handler + `bot.py` entrypoint**

Silent path: no group-visible messages ever; errors only via owner DM.

- [ ] **Step 4: Run FULL suite to verify everything passes**

Run: `pytest tests/ -v -m "not integration"`
Expected: PASS (pins edited-message + no-rights Review lines).

- [ ] **Step 5: Commit**

```bash
git add handlers_group.py bot.py tests/test_group.py
git commit -m "feat: add silent group deletion handler and entrypoint"
```

---

## Self-Review

1. Spec coverage: /start + groups buttons (T5); per-group blocked default-allow (T3/T5); unlimited per-group whitelist + picker (T7); silent delete + private on-demand stats (T8/T5); owner-only control (T5/T7); all-type coverage via classify priority (T2); no-rights DM throttled (T8); PG persistence (T3); membership fresh-start + pending DM (T6); privacy/admin docs (T1). Covered.
2. Step scan: each test step names assertions with spec values; code steps give exact signatures/files; verify steps give command + expected output; no TBDs.
3. Type consistency: `chat_id: int`, `ctype: str`, `blocked: set[str]`, callback strings `group:/toggle:/white:/unwhite:/stats:/reset_*` used identically in T4–T8; `should_delete` kwargs match T8 call sites.
4. Review Focus: all five lines pinned — anonymous (T3), captioned-media (T2), /command exempt (T2+T8), edited recheck (T8), non-owner gate (T5).
5. Proportion: plan lists decisions/interfaces/tests, not bodies; shorter than the code it will produce.
