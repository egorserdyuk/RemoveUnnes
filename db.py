"""PostgreSQL storage + pure moderation decision helpers."""

from __future__ import annotations

import asyncpg

SCHEMA = """
CREATE TABLE IF NOT EXISTS owners (
    user_id BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS groups (
    chat_id BIGINT PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    added_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS blocked (
    chat_id BIGINT NOT NULL,
    ctype TEXT NOT NULL,
    PRIMARY KEY (chat_id, ctype)
);
CREATE TABLE IF NOT EXISTS whitelist (
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username TEXT,
    display TEXT,
    added_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS stats (
    chat_id BIGINT NOT NULL,
    ctype TEXT NOT NULL,
    cnt BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, ctype)
);
CREATE TABLE IF NOT EXISTS pending_greetings (
    owner_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (owner_id, chat_id)
);
CREATE TABLE IF NOT EXISTS notify_state (
    chat_id BIGINT PRIMARY KEY,
    notified_at TIMESTAMPTZ DEFAULT now()
);
"""


def should_delete(
    *,
    ctype: str | None,
    from_user_id: int | None,
    is_bot_self: bool,
    blocked: set[str],
    whitelisted: bool,
    command_exempt: bool,
) -> bool:
    if ctype is None or is_bot_self or command_exempt:
        return False
    if whitelisted:
        return False
    return ctype in blocked


def format_stats(stats: dict[str, int]) -> str:
    nonzero = sorted((c, n) for c, n in stats.items() if n > 0)
    if not nonzero:
        return "nothing removed yet"
    parts = [f"{n} {c if n == 1 else c + 's'}" for c, n in nonzero]
    return "removed messages: " + "; ".join(parts)


async def init_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn)


async def init_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)


async def register_group(pool: asyncpg.Pool, chat_id: int, owner_id: int, title: str) -> str:
    """Record the bot joining a group. Returns created/kept/fresh_start."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT owner_id FROM groups WHERE chat_id = $1", chat_id)
            if row is None:
                await conn.execute(
                    "INSERT INTO owners (user_id) VALUES ($1) ON CONFLICT DO NOTHING", owner_id
                )
                await conn.execute(
                    "INSERT INTO groups (chat_id, owner_id, title, active) VALUES ($1, $2, $3, TRUE)",
                    chat_id,
                    owner_id,
                    title,
                )
                return "created"
            if row["owner_id"] == owner_id:
                await conn.execute(
                    "UPDATE groups SET title = $2, active = TRUE WHERE chat_id = $1",
                    chat_id,
                    title,
                )
                return "kept"
            await conn.execute("DELETE FROM blocked WHERE chat_id = $1", chat_id)
            await conn.execute("DELETE FROM whitelist WHERE chat_id = $1", chat_id)
            await conn.execute("DELETE FROM stats WHERE chat_id = $1", chat_id)
            await conn.execute(
                "INSERT INTO owners (user_id) VALUES ($1) ON CONFLICT DO NOTHING", owner_id
            )
            await conn.execute(
                "UPDATE groups SET owner_id = $2, title = $3, active = TRUE WHERE chat_id = $1",
                chat_id,
                owner_id,
                title,
            )
            return "fresh_start"


async def mark_group_inactive(pool: asyncpg.Pool, chat_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("UPDATE groups SET active = FALSE WHERE chat_id = $1", chat_id)


async def get_owner(pool: asyncpg.Pool, chat_id: int) -> int | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT owner_id FROM groups WHERE chat_id = $1", chat_id)
        return row["owner_id"] if row else None


async def owner_groups(pool: asyncpg.Pool, owner_id: int) -> list[tuple[int, str]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chat_id, title FROM groups WHERE owner_id = $1 AND active ORDER BY title",
            owner_id,
        )
        return [(r["chat_id"], r["title"]) for r in rows]


async def get_blocked(pool: asyncpg.Pool, chat_id: int) -> set[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT ctype FROM blocked WHERE chat_id = $1", chat_id)
        return {r["ctype"] for r in rows}


async def toggle_blocked(pool: asyncpg.Pool, chat_id: int, ctype: str) -> set[str]:
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM blocked WHERE chat_id = $1 AND ctype = $2", chat_id, ctype
        )
        if exists:
            await conn.execute(
                "DELETE FROM blocked WHERE chat_id = $1 AND ctype = $2", chat_id, ctype
            )
        else:
            await conn.execute(
                "INSERT INTO blocked (chat_id, ctype) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                chat_id,
                ctype,
            )
    return await get_blocked(pool, chat_id)


async def is_whitelisted(pool: asyncpg.Pool, chat_id: int, user_id: int) -> bool:
    async with pool.acquire() as conn:
        return bool(
            await conn.fetchval(
                "SELECT 1 FROM whitelist WHERE chat_id = $1 AND user_id = $2", chat_id, user_id
            )
        )


async def add_whitelist(
    pool: asyncpg.Pool, chat_id: int, rows: list[tuple[int, str | None, str | None]]
) -> None:
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO whitelist (chat_id, user_id, username, display)"
            " VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            [(chat_id, uid, uname, disp) for uid, uname, disp in rows],
        )


async def remove_whitelist(pool: asyncpg.Pool, chat_id: int, user_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM whitelist WHERE chat_id = $1 AND user_id = $2", chat_id, user_id
        )


async def get_whitelist(pool: asyncpg.Pool, chat_id: int) -> list[tuple[int, str | None]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username FROM whitelist WHERE chat_id = $1 ORDER BY user_id",
            chat_id,
        )
        return [(r["user_id"], r["username"]) for r in rows]


async def whitelist_count(pool: asyncpg.Pool, chat_id: int) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM whitelist WHERE chat_id = $1", chat_id)


async def incr_stat(pool: asyncpg.Pool, chat_id: int, ctype: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO stats (chat_id, ctype, cnt) VALUES ($1, $2, 1)"
            " ON CONFLICT (chat_id, ctype) DO UPDATE SET cnt = stats.cnt + 1",
            chat_id,
            ctype,
        )


async def get_stats(pool: asyncpg.Pool, chat_id: int) -> dict[str, int]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT ctype, cnt FROM stats WHERE chat_id = $1", chat_id)
        return {r["ctype"]: r["cnt"] for r in rows}


async def reset_stats(pool: asyncpg.Pool, chat_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM stats WHERE chat_id = $1", chat_id)


async def reset_group_data(pool: asyncpg.Pool, chat_id: int) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM blocked WHERE chat_id = $1", chat_id)
            await conn.execute("DELETE FROM whitelist WHERE chat_id = $1", chat_id)
            await conn.execute("DELETE FROM stats WHERE chat_id = $1", chat_id)
