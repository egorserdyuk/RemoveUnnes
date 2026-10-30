from types import SimpleNamespace

from limits import (
    DURATION_TYPES,
    format_window,
    get_duration,
    is_cooldown_ok,
    is_duration_ok,
    parse_window,
)


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


def test_parse_window_max_guard():
    import pytest
    assert parse_window("365d") == 365 * 86400
    for bad in ["366d", "999999999d", "1000000h"]:
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


def test_format_window_round_trip():
    assert format_window(None) == "off"
    assert format_window(30) == "30s"
    assert format_window(60) == "1m"
    assert format_window(7200) == "2h"
    assert format_window(86400) == "1d"
    for raw in ("30s", "1m", "2h", "1d"):
        assert format_window(parse_window(raw)) == raw


def test_duration_types():
    assert DURATION_TYPES == {"voice", "video", "video_note", "audio", "animation"}


def test_get_duration_object_kind():
    fields = SimpleNamespace(
        voice=None,
        video=SimpleNamespace(duration=12),
        video_note=None,
        audio=None,
        animation=None,
    )
    assert get_duration(fields) == 12
