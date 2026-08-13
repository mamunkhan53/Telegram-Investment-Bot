from __future__ import annotations

from app.blockchain.bsc import BSCUSDTAdapter
from app.blockchain.monitor import DepositMonitor
from app.config.settings import Settings
from app.database.session import transaction
from app.services.blockchain_service import BlockchainService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_deposit_cycle(settings: Settings) -> None:
    if not settings.platform_deposit_address or not settings.bsc_usdt_contract_address:
        logger.warning(
            "Deposit monitor skipped because blockchain settings are incomplete"
        )
        return
    async with transaction() as session:
        adapter = BSCUSDTAdapter(settings)
        monitor = DepositMonitor(session, adapter, settings)
        detected = await monitor.scan_once()
        confirmed = await monitor.update_confirmations()
        credited = await BlockchainService(session).credit_confirmed_deposits()
        logger.info(
            "Deposit cycle completed",
            extra={
                "detected": detected,
                "confirmed_updated": confirmed,
                "credited": credited,
            },
        )
