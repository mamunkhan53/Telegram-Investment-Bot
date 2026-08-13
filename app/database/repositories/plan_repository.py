from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import InvestmentPlan
from app.database.models.enums import PlanStatus
from app.database.repositories.base import Repository


class PlanRepository(Repository[InvestmentPlan]):
    model = InvestmentPlan

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_active_for_update(self, plan_id) -> InvestmentPlan:
        statement = (
            select(InvestmentPlan)
            .where(
                InvestmentPlan.id == plan_id,
                InvestmentPlan.status == PlanStatus.ACTIVE,
            )
            .with_for_update()
        )
        result = await self.session.execute(statement)
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ValueError("Investment plan is not active or does not exist.")
        return plan

    async def list_active(self) -> list[InvestmentPlan]:
        statement = (
            select(InvestmentPlan)
            .where(InvestmentPlan.status == PlanStatus.ACTIVE)
            .order_by(InvestmentPlan.sort_order, InvestmentPlan.name)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
