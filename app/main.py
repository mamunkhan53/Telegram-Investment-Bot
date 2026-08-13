from __future__ import annotations

import asyncio
import os

import uvicorn

from app.api.api import app as api_app
from app.bot.bot import build_bot, build_dispatcher
from app.config.settings import get_settings
from app.scheduler.runner import build_scheduler, start_scheduler, stop_scheduler
from app.utils.logger import configure_logging, get_logger


async def run() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)
    process = os.getenv("APP_PROCESS", "all").lower()
    scheduler = build_scheduler(settings)
    if process in {"all", "worker"}:
        start_scheduler(scheduler)

    tasks: list[asyncio.Task] = []
    bot = None
    try:
        if process in {"all", "bot"}:
            bot = build_bot(settings)
            dispatcher = build_dispatcher()
            tasks.append(
                asyncio.create_task(dispatcher.start_polling(bot), name="telegram-bot")
            )
        if process in {"all", "api"}:
            config = uvicorn.Config(
                api_app,
                host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")),
                log_level=settings.log_level.lower(),
            )
            tasks.append(
                asyncio.create_task(uvicorn.Server(config).serve(), name="admin-api")
            )
        if process == "worker":
            tasks.append(
                asyncio.create_task(asyncio.Event().wait(), name="scheduler-worker")
            )
        if not tasks:
            raise ValueError("APP_PROCESS must be one of: all, bot, api, worker")
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        stop_scheduler(scheduler)
        if bot is not None:
            await bot.session.close()
        logger.info("Application stopped")


if __name__ == "__main__":
    asyncio.run(run())
