from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BlockchainScanState, Deposit
from app.database.models.enums import DepositStatus
from app.database.repositories.base import Repository


class DepositRepository(Repository[Deposit]):
    model = Deposit

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_chain_event(
        self, network: str, tx_hash: str, log_index: int, *, for_update: bool = False
    ) -> Deposit | None:
        statement = select(Deposit).where(
            Deposit.network == network,
            Deposit.tx_hash == tx_hash,
            Deposit.log_index == log_index,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_tx_hash(
        self, tx_hash: str, *, for_update: bool = False
    ) -> Deposit | None:
        statement = select(Deposit).where(Deposit.tx_hash == tx_hash)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_detected(self, *, limit: int = 100) -> list[Deposit]:
        statement = (
            select(Deposit)
            .where(Deposit.status == DepositStatus.DETECTED)
            .order_by(Deposit.detected_at)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_confirmed(self, *, limit: int = 100) -> list[Deposit]:
        statement = (
            select(Deposit)
            .where(Deposit.status == DepositStatus.CONFIRMED)
            .order_by(Deposit.confirmed_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


class ScanStateRepository(Repository[BlockchainScanState]):
    model = BlockchainScanState

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_scope(
        self,
        network: str,
        asset: str,
        deposit_address: str,
        *,
        for_update: bool = False,
    ) -> BlockchainScanState | None:
        statement = select(BlockchainScanState).where(
            BlockchainScanState.network == network,
            BlockchainScanState.asset == asset,
            BlockchainScanState.deposit_address == deposit_address,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
