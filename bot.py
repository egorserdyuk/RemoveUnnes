"""Entrypoint: long-polling GoyGram bot."""

import asyncio
import logging

from goygram import GoyGram

import config
import db
import handlers_group
import handlers_membership
import handlers_private


async def main() -> None:
    settings = config.load()
    logging.basicConfig(level=logging.INFO)
    kwargs: dict = {}
    if settings.api_base:
        kwargs["bot_base"] = settings.api_base
        logging.getLogger(__name__).info("using custom Telegram API server: %s", settings.api_base)
    app = GoyGram(bot_token=settings.token, **kwargs)
    pool = await db.init_pool(settings.dsn)
    await db.init_schema(pool)
    me = await app.get_me()
    bot_id = me["id"] if me else 0
    handlers_group.register(app, pool, bot_id)
    handlers_membership.register(app, pool, bot_id)
    handlers_private.register(app, pool)
    app.run()


if __name__ == "__main__":
    asyncio.run(main())
