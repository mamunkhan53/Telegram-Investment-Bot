from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Withdrawal
from app.database.models.enums import WithdrawalStatus
from app.database.repositories.base import Repository


class WithdrawalRepository(Repository[Withdrawal]):
    model = Withdrawal

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_idempotency_key(
        self, idempotency_key: str, *, for_update: bool = False
    ) -> Withdrawal | None:
        statement = select(Withdrawal).where(
            Withdrawal.idempotency_key == idempotency_key
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_for_update(self, withdrawal_id) -> Withdrawal:
        withdrawal = await self.get(withdrawal_id, for_update=True)
        if withdrawal is None:
            raise ValueError("Withdrawal not found.")
        return withdrawal

    async def list_processable(self, *, limit: int = 100) -> list[Withdrawal]:
        statement = (
            select(Withdrawal)
            .where(
                Withdrawal.status.in_(
                    [WithdrawalStatus.REQUESTED, WithdrawalStatus.APPROVED]
                )
            )
            .order_by(Withdrawal.requested_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
