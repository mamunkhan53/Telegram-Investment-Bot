from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Investment,
    InvestmentPlan,
    ReferralReward,
    Transaction,
    User,
    Wallet,
)
from app.database.models.enums import InvestmentStatus, PlanStatus


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def get_wallet(self, user_id, asset: str = "USDT") -> Wallet | None:
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user_id, Wallet.asset == asset)
        )
        return result.scalar_one_or_none()

    async def list_active_plans(self) -> list[InvestmentPlan]:
        result = await self.session.execute(
            select(InvestmentPlan)
            .where(InvestmentPlan.status == PlanStatus.ACTIVE)
            .order_by(InvestmentPlan.sort_order, InvestmentPlan.name)
        )
        return list(result.scalars().all())

    async def list_user_investments(self, user_id, limit: int = 20) -> list[Investment]:
        result = await self.session.execute(
            select(Investment)
            .where(Investment.user_id == user_id)
            .order_by(Investment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def referral_summary(self, user_id) -> tuple[int, Decimal]:
        result = await self.session.execute(
            select(
                func.count(ReferralReward.id),
                func.coalesce(func.sum(ReferralReward.reward_amount), 0),
            ).where(ReferralReward.referrer_id == user_id)
        )
        count, amount = result.one()
        return int(count or 0), Decimal(amount or 0)

    async def transaction_history(self, user_id, limit: int = 20) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def portfolio_profit(self, user_id) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Investment.paid_profit_amount), 0)).where(
                Investment.user_id == user_id,
                Investment.status == InvestmentStatus.COMPLETED,
            )
        )
        return Decimal(result.scalar_one() or 0)
