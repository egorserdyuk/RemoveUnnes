"""Entrypoint: long-polling aiogram bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

import config
import db
import handlers_group
import handlers_membership
import handlers_private
import handlers_whitelist

ALLOWED_UPDATES = ["message", "edited_message", "my_chat_member", "callback_query"]


async def main() -> None:
    settings = config.load()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("allowed_updates=%s", ALLOWED_UPDATES)
    pool = await db.init_pool(settings.dsn)
    await db.init_schema(pool)
    bot = Bot(token=settings.token)
    dp = Dispatcher()
    dp["pool"] = pool
    dp.include_routers(
        handlers_membership.router,
        handlers_private.router,
        handlers_whitelist.router,
        handlers_group.router,
    )
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


if __name__ == "__main__":
    asyncio.run(main())
