from __future__ import annotations

from app.config.settings import Settings
from app.database.session import transaction
from app.services.investment_service import InvestmentService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_investment_cycle(settings: Settings) -> None:
    async with transaction() as session:
        processed = await InvestmentService(session).accrue_due_investments(limit=100)
        logger.info("Investment cycle completed", extra={"processed": processed})
