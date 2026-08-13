from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import MAX_REFERRAL_LEVEL
from app.database.models import Investment, ReferralReward, User
from app.database.models.enums import ReferralStatus, TransactionType
from app.database.repositories.referral_repository import ReferralRepository
from app.database.repositories.wallet_repository import WalletRepository
from app.services.wallet_service import WalletService

DEFAULT_REWARD_RATES = {
    1: Decimal(5),
    2: Decimal(2),
    3: Decimal(1),
}


class ReferralService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.referrals = ReferralRepository(session)
        self.wallets = WalletRepository(session)
        self.wallet_service = WalletService(session)

    async def distribute_for_investment(
        self,
        *,
        investment: Investment,
        reward_rates: dict[int, Decimal] | None = None,
    ) -> int:
        rates = reward_rates or DEFAULT_REWARD_RATES
        referred_user = await self.session.get(User, investment.user_id)
        if referred_user is None:
            raise ValueError("Investment owner does not exist.")

        current_referrer_id = referred_user.referred_by_id
        distributed = 0
        for level in range(1, MAX_REFERRAL_LEVEL + 1):
            if current_referrer_id is None:
                break
            referrer = await self.session.get(User, current_referrer_id)
            if referrer is None:
                break
            percent = Decimal(str(rates.get(level, Decimal(0))))
            if percent <= 0:
                current_referrer_id = referrer.referred_by_id
                continue
            reward_amount = (
                investment.principal_amount * percent / Decimal(100)
            ).quantize(Decimal("0.000000000000000001"))
            existing = await self.referrals.get_source_reward(
                referrer.id, referred_user.id, investment.id
            )
            if existing is not None:
                current_referrer_id = referrer.referred_by_id
                continue

            wallet = await self.wallets.get_by_user_and_asset(
                referrer.id, "USDT", for_update=True
            )
            if wallet is None:
                wallet = await self.wallets.get_or_create_for_user(
                    referrer.id, asset="USDT", network="BSC"
                )
            reward = ReferralReward(
                referrer_id=referrer.id,
                referred_user_id=referred_user.id,
                source_investment_id=investment.id,
                level=level,
                reward_percent=percent,
                reward_amount=reward_amount,
                status=ReferralStatus.PENDING,
            )
            await self.referrals.add(reward)
            await self.wallet_service.credit(
                wallet_id=wallet.id,
                user_id=referrer.id,
                amount=reward_amount,
                transaction_type=TransactionType.REFERRAL_REWARD,
                idempotency_key=f"referral-reward:{investment.id}:{level}:{referrer.id}",
                reference_type="referral_reward",
                reference_id=reward.id,
                extra_data={"level": level, "source_investment_id": str(investment.id)},
            )
            reward.status = ReferralStatus.PAID
            reward.paid_at = datetime.now(timezone.utc)
            distributed += 1
            current_referrer_id = referrer.referred_by_id
        await self.session.flush()
        return distributed
