from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Investment
from app.database.models.enums import InvestmentStatus, TransactionType
from app.database.repositories.ledger_repository import InvestmentRepository
from app.database.repositories.plan_repository import PlanRepository
from app.database.repositories.wallet_repository import WalletRepository
from app.services.wallet_service import WalletService
from app.utils.validators import parse_positive_amount, validate_idempotency_key


class InvestmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plans = PlanRepository(session)
        self.investments = InvestmentRepository(session)
        self.wallets = WalletRepository(session)
        self.wallet_service = WalletService(session)

    async def create_investment(
        self,
        *,
        user_id,
        plan_id,
        amount: Decimal,
        auto_reinvest: bool,
        idempotency_key: str,
    ) -> Investment:
        amount = parse_positive_amount(amount)
        idempotency_key = validate_idempotency_key(idempotency_key)
        plan = await self.plans.get_active_for_update(plan_id)
        if amount < plan.minimum_amount:
            raise ValueError("Investment amount is below the plan minimum.")
        if plan.maximum_amount is not None and amount > plan.maximum_amount:
            raise ValueError("Investment amount exceeds the plan maximum.")
        if auto_reinvest and not plan.auto_reinvest_allowed:
            raise ValueError("Automatic reinvestment is not enabled for this plan.")

        wallet = await self.wallets.get_by_user_and_asset(
            user_id, plan.asset, for_update=True
        )
        if wallet is None:
            raise ValueError("User wallet does not exist.")

        existing_transaction = (
            await self.wallet_service.transactions.get_by_idempotency_key(
                f"investment-debit:{idempotency_key}", for_update=True
            )
        )
        if existing_transaction is not None:
            existing_investment = await self.investments.get(
                existing_transaction.reference_id
            )
            if existing_investment is None:
                raise RuntimeError(
                    "Investment debit exists without its investment record."
                )
            return existing_investment

        now = datetime.now(timezone.utc)
        maturity_at = now + timedelta(days=plan.duration_days)
        await self.wallet_service.debit(
            wallet_id=wallet.id,
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.INVESTMENT,
            idempotency_key=f"investment-debit:{idempotency_key}",
            reference_type="investment",
            extra_data={"plan_id": str(plan.id)},
        )
        investment = Investment(
            user_id=user_id,
            plan_id=plan.id,
            principal_amount=amount,
            profit_amount=Decimal(0),
            paid_profit_amount=Decimal(0),
            status=InvestmentStatus.ACTIVE,
            started_at=now,
            maturity_at=maturity_at,
            next_accrual_at=maturity_at,
            auto_reinvest=auto_reinvest,
        )
        await self.investments.add(investment)
        await self.session.flush()
        transaction = await self.wallet_service.transactions.get_by_idempotency_key(
            f"investment-debit:{idempotency_key}", for_update=True
        )
        if transaction is not None:
            transaction.reference_id = investment.id
        return investment

    async def accrue_due_investments(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> int:
        now = now or datetime.now(timezone.utc)
        due = await self.investments.list_due(now, limit=limit)
        processed = 0
        for investment in due:
            plan = await self.plans.get(investment.plan_id)
            if plan is None:
                raise RuntimeError("Investment references a missing plan.")
            wallet = await self.wallets.get_by_user_and_asset(
                investment.user_id, plan.asset, for_update=True
            )
            if wallet is None:
                raise RuntimeError("Investment owner wallet is missing.")
            profit = (
                investment.principal_amount * plan.profit_rate / Decimal(100)
            ).quantize(Decimal("0.000000000000000001"))
            await self.wallet_service.credit(
                wallet_id=wallet.id,
                user_id=investment.user_id,
                amount=profit,
                transaction_type=TransactionType.PROFIT,
                idempotency_key=f"investment-profit:{investment.id}",
                reference_type="investment",
                reference_id=investment.id,
                extra_data={"plan_id": str(plan.id)},
            )
            investment.profit_amount = profit
            investment.paid_profit_amount = profit
            investment.status = InvestmentStatus.COMPLETED
            investment.completed_at = now
            investment.next_accrual_at = None
            investment.version += 1
            processed += 1
        await self.session.flush()
        return processed
