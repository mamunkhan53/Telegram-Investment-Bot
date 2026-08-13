from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def send_user_message(self, telegram_user_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(telegram_user_id, text)
            return True
        except TelegramAPIError:
            logger.exception(
                "Telegram notification failed",
                extra={"telegram_user_id": telegram_user_id},
            )
            return False
