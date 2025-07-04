"""
bot/entry.py
-------------
Bootstrap script that wires every router and starts polling.
Keep this file tiny: all heavy logic lives in the routers or helpers.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot import runtime as r

from bot.config import settings
from bot.logger import logger
from bot.forwarding import ForwardManager

from bot.routers.auth import router as auth_router
from bot.routers.sources import router as sources_router
from bot.routers.targets import router as targets_router
from bot.routers.filters import router as filters_router
from bot.routers.misc    import router as misc_router

# ----------------------------------------------------------------------------
# Instantiate core services (singletons shared across the package)
# ----------------------------------------------------------------------------


bot = Bot(
    settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

dp.include_router(auth_router)
dp.include_router(sources_router)
dp.include_router(targets_router)
dp.include_router(filters_router)
dp.include_router(misc_router)

# ----------------------------------------------------------------------------
# Startup / shutdown helpers
# ----------------------------------------------------------------------------

async def _on_startup():
    await r.db.init()
    r.forwarder = ForwardManager(r.db, r.auth)


async def _on_shutdown() -> None:
    if r.forwarder:
        await r.forwarder.stop_all()
    logger.info("Bot stopped")


async def main() -> None:
    # Stream logs to stdout (visible in Docker)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    await _on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await _on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
