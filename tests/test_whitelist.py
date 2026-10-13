from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import texts


def make_callback(data, user_id):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=999, type="private"),
            edit_text=AsyncMock(),
            answer=AsyncMock(),
        ),
        answer=AsyncMock(),
    )


def make_shared(user_ids, owner_id=111):
    users = [SimpleNamespace(user_id=u, first_name=None, last_name=None, username=None, photo=None) for u in user_ids]
    return SimpleNamespace(
        chat=SimpleNamespace(id=999, type="private"),
        from_user=SimpleNamespace(id=owner_id),
        users_shared=SimpleNamespace(request_id=7, users=users),
        answer=AsyncMock(),
    )


async def test_users_shared_adds_all_ids():
    from handlers_whitelist import on_users_shared

    msg = make_shared([11, 22, 33])
    pool = object()
    with (
        patch("handlers_whitelist.get_owner", AsyncMock(return_value=111)),
        patch("handlers_whitelist.add_whitelist", AsyncMock()) as aw,
    ):
        with patch("handlers_whitelist.pending_pick", {7: -1001}):
            await on_users_shared(msg, pool)
    rows = aw.call_args[0][2]
    assert sorted(u for u, _, _ in rows) == [11, 22, 33]


async def test_unwhite_requires_owner():
    from handlers_whitelist import on_unwhite

    cb = make_callback("unwhite:-1001:11", 555)
    pool = object()
    with (
        patch("handlers_whitelist.get_owner", AsyncMock(return_value=111)),
        patch("handlers_whitelist.remove_whitelist") as rw,
    ):
        await on_unwhite(cb, pool)
    rw.assert_not_called()
    cb.answer.assert_called_once_with(texts.NOT_OWNER, show_alert=True)
