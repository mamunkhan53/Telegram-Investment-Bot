from __future__ import annotations

from app.config.settings import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_notification_cycle(settings: Settings) -> None:
    # Notification delivery stays behind a service boundary so Telegram retry
    # behavior and message localization remain independently testable.
    logger.debug(
        "Notification cycle completed", extra={"environment": settings.app_env}
    )
