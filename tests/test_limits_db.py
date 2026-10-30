"""Limits settings storage tests (FakePool, no live DB)."""

from db import (
    SCHEMA,
    clear_limit,
    get_limit,
    get_limits,
    register_group,
    reset_group_data,
    set_limit,
)


class _FakeTransaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, pool):
        self._pool = pool

    def transaction(self):
        return _FakeTransaction()

    async def execute(self, query, *args):
        q = " ".join(query.split())
        if q.startswith("INSERT INTO limits"):
            self._pool._limits[(args[0], args[1])] = (args[2], args[3])
            return "INSERT 0 1"
        if q.startswith("DELETE FROM limits"):
            if "AND ctype" in q:
                self._pool._limits.pop((args[0], args[1]), None)
            else:
                for k in [k for k in self._pool._limits if k[0] == args[0]]:
                    del self._pool._limits[k]
            return "DELETE 0"
        if q.startswith("DELETE FROM blocked"):
            return "DELETE 0"
        if q.startswith("DELETE FROM whitelist"):
            return "DELETE 0"
        if q.startswith("DELETE FROM stats"):
            return "DELETE 0"
        if q.startswith("INSERT INTO owners"):
            return "INSERT 0 1"
        if q.startswith("INSERT INTO groups"):
            self._pool._groups[args[0]] = {"owner_id": args[1], "title": args[2]}
            return "INSERT 0 1"
        if q.startswith("UPDATE groups"):
            chat_id, owner_id, title = args[0], args[1], args[2]
            if chat_id in self._pool._groups:
                self._pool._groups[chat_id].update(owner_id=owner_id, title=title)
            return "UPDATE 1"
        raise AssertionError(f"unexpected query: {query!r}")

    async def fetchrow(self, query, *args):
        q = " ".join(query.split())
        if "FROM limits" in q:
            v = self._pool._limits.get((args[0], args[1]))
            if v is None:
                return None
            return {"max_duration_sec": v[0], "cooldown_sec": v[1]}
        if "FROM groups" in q:
            g = self._pool._groups.get(args[0])
            if g is None:
                return None
            return {"owner_id": g["owner_id"]}
        raise AssertionError(f"unexpected query: {query!r}")

    async def fetch(self, query, *args):
        q = " ".join(query.split())
        if "FROM limits" in q:
            return [
                {"ctype": ctype, "max_duration_sec": dur, "cooldown_sec": cool}
                for (chat_id, ctype), (dur, cool) in sorted(self._pool._limits.items())
                if chat_id == args[0]
            ]
        raise AssertionError(f"unexpected query: {query!r}")


class _FakeAcquire:
    def __init__(self, pool):
        self._pool = pool

    async def __aenter__(self):
        return FakeConn(self._pool)

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self):
        self._limits: dict[tuple[int, str], tuple[int | None, int | None]] = {}
        self._groups: dict[int, dict] = {}

    def acquire(self):
        return _FakeAcquire(self)


async def test_set_get_clear_limit():
    pool = FakePool()
    await set_limit(pool, -1001, "voice", 60, 30)
    assert await get_limit(pool, -1001, "voice") == (60, 30)
    await clear_limit(pool, -1001, "voice")
    assert await get_limit(pool, -1001, "voice") == (None, None)


async def test_get_limit_missing_returns_none_none():
    pool = FakePool()
    assert await get_limit(pool, -1001, "voice") == (None, None)


async def test_set_limit_upsert_overwrites():
    pool = FakePool()
    await set_limit(pool, -1001, "voice", 60, 30)
    await set_limit(pool, -1001, "voice", 120, None)
    assert await get_limit(pool, -1001, "voice") == (120, None)


async def test_get_limits_returns_all_types():
    pool = FakePool()
    await set_limit(pool, -1001, "voice", 60, 30)
    await set_limit(pool, -1001, "text", None, 60)
    await set_limit(pool, -1002, "voice", 90, 10)
    assert await get_limits(pool, -1001) == {"voice": (60, 30), "text": (None, 60)}
    assert await get_limits(pool, -9999) == {}


async def test_reset_group_data_clears_limits():
    pool = FakePool()
    await set_limit(pool, -1001, "voice", 60, 30)
    await reset_group_data(pool, -1001)
    assert await get_limit(pool, -1001, "voice") == (None, None)
    assert await get_limits(pool, -1001) == {}


async def test_register_group_fresh_start_clears_limits():
    pool = FakePool()
    pool._groups[-1001] = {"owner_id": 111, "title": "G"}
    await set_limit(pool, -1001, "voice", 60, 30)
    assert await register_group(pool, -1001, 222, "G") == "fresh_start"
    assert await get_limit(pool, -1001, "voice") == (None, None)


def test_schema_includes_limits_table():
    assert "CREATE TABLE IF NOT EXISTS limits" in SCHEMA
    assert "PRIMARY KEY (chat_id, ctype)" in SCHEMA
