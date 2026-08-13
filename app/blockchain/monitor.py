from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.wallet import BlockchainWallet
from app.config.settings import Settings
from app.database.models import BlockchainScanState, Deposit
from app.database.models.enums import DepositStatus
from app.database.repositories.deposit_repository import (
    DepositRepository,
    ScanStateRepository,
)
from app.database.repositories.wallet_repository import WalletRepository
from app.utils.validators import validate_bsc_address


class DepositMonitor:
    def __init__(
        self, session: AsyncSession, adapter: BlockchainWallet, settings: Settings
    ) -> None:
        self.session = session
        self.adapter = adapter
        self.settings = settings
        self.deposits = DepositRepository(session)
        self.scan_states = ScanStateRepository(session)
        self.wallets = WalletRepository(session)

    async def scan_once(self, *, max_blocks: int = 500) -> int:
        deposit_address = validate_bsc_address(
            self.settings.platform_deposit_address or ""
        )
        latest = await self.adapter.latest_block_number()
        state = await self.scan_states.get_scope(
            self.adapter.network,
            self.adapter.asset,
            deposit_address,
            for_update=True,
        )
        if state is None:
            state = await self.scan_states.add(
                BlockchainScanState(
                    network=self.adapter.network,
                    asset=self.adapter.asset,
                    deposit_address=deposit_address,
                    last_scanned_block=max(
                        0, latest - self.settings.bsc_confirmations_required
                    ),
                )
            )
        from_block = state.last_scanned_block + 1
        to_block = min(latest, from_block + max_blocks - 1)
        if from_block > to_block:
            return 0

        transfers = await self.adapter.transfers_to_address(
            address=deposit_address,
            from_block=from_block,
            to_block=to_block,
        )
        created = 0
        for transfer in transfers:
            existing = await self.deposits.get_by_chain_event(
                transfer.network,
                transfer.tx_hash,
                transfer.log_index,
                for_update=True,
            )
            if existing is not None:
                continue
            wallet = await self.wallets.get_by_user_and_asset_from_deposit_address(
                transfer.to_address,
                transfer.asset,
            )
            if wallet is None:
                continue
            deposit = Deposit(
                user_id=wallet.user_id,
                wallet_id=wallet.id,
                network=transfer.network,
                asset=transfer.asset,
                tx_hash=transfer.tx_hash,
                log_index=transfer.log_index,
                from_address=transfer.from_address,
                to_address=transfer.to_address,
                amount=transfer.amount,
                block_number=transfer.block_number,
                confirmations=0,
                status=DepositStatus.DETECTED,
                detected_at=datetime.now(timezone.utc),
            )
            await self.deposits.add(deposit)
            created += 1
        state.last_scanned_block = to_block
        await self.session.flush()
        return created

    async def update_confirmations(self, *, limit: int = 100) -> int:
        pending = await self.deposits.list_detected(limit=limit)
        updated = 0
        for deposit in pending:
            confirmations = await self.adapter.transaction_confirmations(
                deposit.tx_hash
            )
            deposit.confirmations = confirmations
            if confirmations >= self.settings.bsc_confirmations_required:
                deposit.status = DepositStatus.CONFIRMED
                deposit.confirmed_at = datetime.now(timezone.utc)
            updated += 1
        await self.session.flush()
        return updated
