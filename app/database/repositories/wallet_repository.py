from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Wallet
from app.database.models.enums import WalletStatus
from app.database.repositories.base import Repository


class WalletRepository(Repository[Wallet]):
    model = Wallet

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_and_asset(
        self,
        user_id,
        asset: str = "USDT",
        *,
        for_update: bool = False,
    ) -> Wallet | None:
        statement = select(Wallet).where(
            Wallet.user_id == user_id, Wallet.asset == asset
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_user_and_asset_from_deposit_address(
        self, deposit_address: str, asset: str = "USDT"
    ) -> Wallet | None:
        statement = select(Wallet).where(
            Wallet.deposit_address == deposit_address, Wallet.asset == asset
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_for_user(
        self, user_id, *, asset: str = "USDT", network: str = "BSC"
    ) -> Wallet:
        wallet = await self.get_by_user_and_asset(user_id, asset, for_update=True)
        if wallet is None:
            wallet = Wallet(
                user_id=user_id,
                asset=asset,
                network=network,
                status=WalletStatus.ACTIVE,
            )
            self.session.add(wallet)
            await self.session.flush()
        return wallet

    async def get_active_for_update(self, wallet_id) -> Wallet:
        wallet = await self.get(wallet_id, for_update=True)
        if wallet is None:
            raise ValueError("Wallet not found.")
        if wallet.status != WalletStatus.ACTIVE:
            raise ValueError("Wallet is not active.")
        return wallet
