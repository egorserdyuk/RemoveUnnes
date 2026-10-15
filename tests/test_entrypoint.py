from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from config import Settings


def make_app():
    return SimpleNamespace(
        get_me=AsyncMock(return_value={"id": 777}),
        run=AsyncMock(),
    )


async def test_main_awaits_run_and_registers_handlers():
    import bot

    app = make_app()
    settings = Settings(token="t", dsn="d", api_base="http://localhost:8081")
    with (
        patch("config.load", return_value=settings),
        patch("bot.GoyGram", return_value=app) as factory,
        patch("db.init_pool", AsyncMock()),
        patch("db.init_schema", AsyncMock()),
        patch("handlers_group.register") as rg,
        patch("handlers_membership.register") as rm,
        patch("handlers_private.register") as rp,
    ):
        await bot.main()
    assert app.run.await_count == 1
    factory.assert_called_once_with(bot_token="t", bot_base="http://localhost:8081")
    rg.assert_called_once()
    rm.assert_called_once()
    rp.assert_called_once()
    assert rg.call_args[0][2] == 777
    assert rm.call_args[0][2] == 777


async def test_main_without_custom_api_base():
    import bot

    app = make_app()
    settings = Settings(token="t", dsn="d", api_base=None)
    with (
        patch("config.load", return_value=settings),
        patch("bot.GoyGram", return_value=app) as factory,
        patch("db.init_pool", AsyncMock()),
        patch("db.init_schema", AsyncMock()),
        patch("handlers_group.register", MagicMock()),
        patch("handlers_membership.register", MagicMock()),
        patch("handlers_private.register", MagicMock()),
    ):
        await bot.main()
    factory.assert_called_once_with(bot_token="t")
    assert app.run.await_count == 1
