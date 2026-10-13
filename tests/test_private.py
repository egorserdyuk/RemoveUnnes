from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import texts


def make_callback(data, user_id):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=999, type="private"),
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )


async def test_non_owner_tap_changes_nothing():
    from handlers_private import on_group_selected

    cb = make_callback("group:-1001", 555)
    pool = object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("handlers_private.get_blocked") as gb,
        patch("handlers_private.whitelist_count") as wc,
    ):
        await on_group_selected(cb, pool)
    gb.assert_not_called()
    wc.assert_not_called()
    cb.answer.assert_called_once_with(texts.NOT_OWNER, show_alert=True)


async def test_toggle_roundtrip_updates_blocked():
    from handlers_private import on_toggle

    cb = make_callback("toggle:-1001:photo", 111)
    pool = object()
    with (
        patch("handlers_private.get_owner", AsyncMock(return_value=111)),
        patch("handlers_private.toggle_blocked", AsyncMock(return_value={"photo"})) as tb,
        patch("handlers_private.owner_groups", AsyncMock(return_value=[(-1001, "G")])),
    ):
        await on_toggle(cb, pool)
    tb.assert_called_once_with(pool, -1001, "photo")
    assert cb.message.edit_text.await_count == 1
