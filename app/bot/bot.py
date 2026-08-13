from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router
from app.config.settings import Settings


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(menu_router)
    return dispatcher


def build_bot(settings: Settings) -> Bot:
    if settings.telegram_bot_token is None:
        raise ValueError("TELEGRAM_BOT_TOKEN is required to start the bot.")
    return Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def run_polling(settings: Settings) -> None:
    bot = build_bot(settings)
    dispatcher = build_dispatcher()
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
