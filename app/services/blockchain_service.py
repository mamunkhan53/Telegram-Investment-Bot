from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.enums import DepositStatus, TransactionType
from app.database.repositories.deposit_repository import DepositRepository
from app.database.repositories.wallet_repository import WalletRepository
from app.services.wallet_service import WalletService


class BlockchainService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.deposits = DepositRepository(session)
        self.wallets = WalletRepository(session)
        self.wallet_service = WalletService(session)

    async def credit_confirmed_deposits(self, *, limit: int = 100) -> int:
        confirmed = await self.deposits.list_confirmed(limit=limit)
        credited = 0
        for deposit in confirmed:
            wallet = await self.wallets.get_active_for_update(deposit.wallet_id)
            if wallet.user_id != deposit.user_id:
                raise RuntimeError(
                    "Deposit wallet does not belong to the deposit user."
                )
            await self.wallet_service.credit(
                wallet_id=wallet.id,
                user_id=deposit.user_id,
                amount=deposit.amount,
                transaction_type=TransactionType.DEPOSIT,
                idempotency_key=f"deposit:{deposit.network}:{deposit.tx_hash}:{deposit.log_index}",
                reference_type="deposit",
                reference_id=deposit.id,
                external_reference=deposit.tx_hash,
                extra_data={
                    "block_number": deposit.block_number,
                    "confirmations": deposit.confirmations,
                },
            )
            deposit.status = DepositStatus.CREDITED
            deposit.credited_at = datetime.now(timezone.utc)
            credited += 1
        await self.session.flush()
        return credited
