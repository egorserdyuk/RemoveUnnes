"""Group limits enforcement: duration caps + per-user cooldowns (Task 3)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from handlers_group import handle_group_message
from test_group import GMsg, make_app, make_msg, sender


def _base_patches(**over):
    kw = dict(
        get_blocked=AsyncMock(return_value=set()),
        is_whitelisted=AsyncMock(return_value=False),
        get_notify=AsyncMock(return_value=False),
        incr_stat=AsyncMock(),
        get_limit=AsyncMock(return_value=(None, None)),
    )
    kw.update(over)
    return kw


def _stack(patches, store):
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("handlers_group.get_blocked", patches["get_blocked"]))
    stack.enter_context(patch("handlers_group.is_whitelisted", patches["is_whitelisted"]))
    stack.enter_context(patch("handlers_group.get_notify", patches["get_notify"]))
    stack.enter_context(patch("handlers_group.incr_stat", patches["incr_stat"]))
    stack.enter_context(patch("handlers_group.get_limit", patches["get_limit"]))
    stack.enter_context(patch("handlers_group._cooldown_last", store))
    return stack


async def test_voice_over_duration_deleted():
    msg = GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}}))
    app, pool = make_app(), object()
    with (patch("handlers_group.get_blocked", AsyncMock(return_value=set())), patch("handlers_group.is_whitelisted", AsyncMock(return_value=False)), patch("handlers_group.get_notify", AsyncMock(return_value=False)), patch("handlers_group.incr_stat", AsyncMock()) as incr, patch("handlers_group.get_limit", AsyncMock(return_value=(60, None))), patch("handlers_group._cooldown_last", {})):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_called_once()
    incr.assert_called_once()


async def test_voice_under_duration_passes_and_records():
    msg = GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 30}}))
    app, pool, store = make_app(), object(), {}
    now = datetime.now(timezone.utc)
    patches = _base_patches(get_limit=AsyncMock(return_value=(60, 30)))
    with _stack(patches, store), patch("handlers_group._now", return_value=now):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_not_called()
    patches["incr_stat"].assert_not_called()
    assert store[(-1001, 111, "voice")] == now


async def test_cooldown_second_send_deleted_first_passes():
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    patches = _base_patches(get_limit=AsyncMock(return_value=(None, 30)))
    with _stack(patches, store), patch("handlers_group._now", return_value=now):
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "hi"})), 777)
        assert store[(-1001, 111, "text")] == now
        app.delete_msg.assert_not_called()
        patches["incr_stat"].assert_not_called()
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "again"})), 777)
    app.delete_msg.assert_called_once_with(-1001, 1)
    patches["incr_stat"].assert_called_once_with(pool, -1001, "text")
    # deleted retry must not extend the window
    assert store[(-1001, 111, "text")] == now


async def test_cooldown_buckets_are_per_user():
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    patches = _base_patches(get_limit=AsyncMock(return_value=(None, 30)))
    with _stack(patches, store), patch("handlers_group._now", return_value=now):
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(uid=111), "text": "a"})), 777)
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(uid=222), "text": "b"})), 777)
        app.delete_msg.assert_not_called()
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(uid=111), "text": "c"})), 777)
    app.delete_msg.assert_called_once()
    assert set(store) == {(-1001, 111, "text"), (-1001, 222, "text")}


async def test_whitelisted_bypasses_limits_without_lookup():
    msg = GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}}))
    app, pool = make_app(), object()
    get_limit = AsyncMock(return_value=(60, 30))
    with (patch("handlers_group.get_blocked", AsyncMock(return_value=set())), patch("handlers_group.is_whitelisted", AsyncMock(return_value=True)), patch("handlers_group.get_limit", get_limit), patch("handlers_group._cooldown_last", {})):
        await handle_group_message(pool, app, msg, 777)
    app.delete_msg.assert_not_called()
    get_limit.assert_not_called()


def _cross_type_patches():
    async def get_limit(pool, chat_id, ctype):
        return {"voice": (60, 30), "text": (None, 30)}[ctype]

    return dict(
        get_blocked=AsyncMock(return_value=set()),
        is_whitelisted=AsyncMock(return_value=False),
        get_notify=AsyncMock(return_value=False),
        incr_stat=AsyncMock(),
        get_limit=AsyncMock(side_effect=get_limit),
    )


async def test_duration_fail_does_not_seed_cooldown():
    """An over-long voice must not start a voice cooldown window."""
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    with _stack(_cross_type_patches(), store), patch("handlers_group._now", return_value=now):
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}})), 777
        )
        assert store == {}
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 30}})), 777
        )
    assert app.delete_msg.call_count == 1
    assert store == {(-1001, 111, "voice"): now}


async def test_cross_type_voice_duration_fail_then_text_passes():
    """A duration delete for voice must not count against the text window."""
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    with _stack(_cross_type_patches(), store), patch("handlers_group._now", return_value=now):
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}})), 777
        )
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "hi"})), 777)
    assert app.delete_msg.call_count == 1
    assert store == {(-1001, 111, "text"): now}


async def test_cross_type_text_activity_ignores_voice():
    """Text passes must not seed the voice window; voice duration fail must not touch it."""
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    with _stack(_cross_type_patches(), store), patch("handlers_group._now", return_value=now):
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "hi"})), 777)
        assert store == {(-1001, 111, "text"): now}
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}})), 777
        )
        assert store == {(-1001, 111, "text"): now}
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 30}})), 777
        )
    assert app.delete_msg.call_count == 1
    assert store == {(-1001, 111, "text"): now, (-1001, 111, "voice"): now}


def _notify_on_patches(**over):
    kw = dict(
        get_blocked=AsyncMock(return_value=set()),
        is_whitelisted=AsyncMock(return_value=False),
        incr_stat=AsyncMock(),
        get_notify=AsyncMock(return_value=True),
        get_owner=AsyncMock(return_value=111),
        get_owner_lang=AsyncMock(return_value="en"),
    )
    kw.update(over)
    return kw


def _stack_notify(patches, store):
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("handlers_group.get_blocked", patches["get_blocked"]))
    stack.enter_context(patch("handlers_group.is_whitelisted", patches["is_whitelisted"]))
    stack.enter_context(patch("handlers_group.incr_stat", patches["incr_stat"]))
    stack.enter_context(patch("handlers_group.get_notify", patches["get_notify"]))
    stack.enter_context(patch("handlers_group.get_owner", patches["get_owner"]))
    stack.enter_context(patch("handlers_group.get_owner_lang", patches["get_owner_lang"]))
    stack.enter_context(patch("handlers_group._cooldown_last", store))
    return stack


async def test_duration_fail_notice_uses_duration_reason():
    app, pool, store = make_app(), object(), {}
    patches = _notify_on_patches(get_limit=AsyncMock(return_value=(60, None)))
    with (
        _stack_notify(patches, store),
        patch("handlers_group.get_limit", patches["get_limit"]),
        patch("handlers_group._recent_notice_texts", {}),
        patch("handlers_group.render_unique_notice", return_value="N") as ru,
    ):
        await handle_group_message(
            pool, app, GMsg(make_msg(**{"from": sender(), "voice": {"file_id": "v", "duration": 65}})), 777
        )
    ru.assert_called_once_with("@bob", "voice", [], reason="duration")


async def test_cooldown_fail_notice_uses_cooldown_reason():
    now = datetime.now(timezone.utc)
    app, pool, store = make_app(), object(), {}
    patches = _notify_on_patches(get_limit=AsyncMock(return_value=(None, 30)))
    with (
        _stack_notify(patches, store),
        patch("handlers_group.get_limit", patches["get_limit"]),
        patch("handlers_group._recent_notice_texts", {}),
        patch("handlers_group.render_unique_notice", return_value="N") as ru,
        patch("handlers_group._now", return_value=now),
    ):
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "hi"})), 777)
        await handle_group_message(pool, app, GMsg(make_msg(**{"from": sender(), "text": "again"})), 777)
    ru.assert_called_once_with("@bob", "text", [], reason="cooldown")
