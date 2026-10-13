import pytest

from config import load


def test_load_missing_env_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        load()
