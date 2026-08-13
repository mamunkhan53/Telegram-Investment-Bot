from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Investment, Transaction
from app.database.models.enums import InvestmentStatus
from app.database.repositories.base import Repository


class TransactionRepository(Repository[Transaction]):
    model = Transaction

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_idempotency_key(
        self, idempotency_key: str, *, for_update: bool = False
    ) -> Transaction | None:
        statement = select(Transaction).where(
            Transaction.idempotency_key == idempotency_key
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


class InvestmentRepository(Repository[Investment]):
    model = Investment

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_for_update(self, investment_id) -> Investment:
        investment = await self.get(investment_id, for_update=True)
        if investment is None:
            raise ValueError("Investment not found.")
        return investment

    async def list_due(self, now: datetime, *, limit: int = 100) -> list[Investment]:
        statement = (
            select(Investment)
            .where(
                Investment.status == InvestmentStatus.ACTIVE,
                Investment.next_accrual_at.is_not(None),
                Investment.next_accrual_at <= now,
            )
            .order_by(Investment.next_accrual_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
