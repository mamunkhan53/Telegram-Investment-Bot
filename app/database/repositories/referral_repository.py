from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ReferralReward
from app.database.repositories.base import Repository


class ReferralRepository(Repository[ReferralReward]):
    model = ReferralReward

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_source_reward(
        self, referrer_id, referred_user_id, source_investment_id
    ) -> ReferralReward | None:
        statement = (
            select(ReferralReward)
            .where(
                ReferralReward.referrer_id == referrer_id,
                ReferralReward.referred_user_id == referred_user_id,
                ReferralReward.source_investment_id == source_investment_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
