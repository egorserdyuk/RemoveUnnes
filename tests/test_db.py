import pytest

from db import format_stats, should_delete


def test_should_delete_anonymous_by_type():
    assert (
        should_delete(
            ctype="photo",
            from_user_id=None,
            is_bot_self=False,
            blocked={"photo"},
            whitelisted=False,
            command_exempt=False,
        )
        is True
    )


def test_should_delete_whitelisted_bypass():
    assert (
        should_delete(
            ctype="photo",
            from_user_id=123,
            is_bot_self=False,
            blocked={"photo"},
            whitelisted=True,
            command_exempt=False,
        )
        is False
    )


def test_should_delete_command_exempt():
    assert (
        should_delete(
            ctype="text",
            from_user_id=123,
            is_bot_self=False,
            blocked={"text"},
            whitelisted=False,
            command_exempt=True,
        )
        is False
    )


def test_should_delete_service_none_and_self_and_unblocked():
    kw = dict(from_user_id=1, is_bot_self=False, blocked={"photo"}, whitelisted=False, command_exempt=False)
    assert should_delete(ctype=None, **kw) is False
    assert should_delete(ctype="photo", is_bot_self=True, from_user_id=None, blocked={"photo"}, whitelisted=False, command_exempt=False) is False
    assert should_delete(ctype="video", **kw) is False


def test_format_stats_order_and_empty():
    assert format_stats({}) == "nothing removed yet"
    assert format_stats({"video": 2, "photo": 1}) == "removed messages: 1 photo; 2 videos"
