import pytest

from config import load


def test_load_missing_env_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        load()


def test_load_api_base_optional(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("POSTGRES_DSN", "d")
    monkeypatch.delenv("TELEGRAM_API_URL", raising=False)
    assert load().api_base is None
    monkeypatch.setenv("TELEGRAM_API_URL", "http://localhost:8082")
    assert load().api_base == "http://localhost:8082"
