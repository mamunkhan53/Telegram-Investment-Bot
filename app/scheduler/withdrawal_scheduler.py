from __future__ import annotations

from app.config.settings import Settings
from app.database.repositories.withdrawal_repository import WithdrawalRepository
from app.database.session import transaction
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_withdrawal_cycle(settings: Settings) -> None:
    async with transaction() as session:
        withdrawals = await WithdrawalRepository(session).list_processable(limit=100)
        logger.info(
            "Withdrawal cycle discovered processable requests",
            extra={"count": len(withdrawals)},
        )
        # Outbound signing is deliberately delegated to an audited signer adapter.
        # Until that adapter is configured, requests remain visible for admin processing.
