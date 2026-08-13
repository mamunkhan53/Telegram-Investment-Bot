from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, Withdrawal
from app.database.models.enums import (
    TransactionStatus,
    TransactionType,
    WithdrawalStatus,
)
from app.database.repositories.ledger_repository import TransactionRepository
from app.database.repositories.wallet_repository import WalletRepository
from app.database.repositories.withdrawal_repository import WithdrawalRepository
from app.utils.validators import (
    parse_nonnegative_amount,
    parse_positive_amount,
    validate_bsc_address,
    validate_idempotency_key,
    validate_transaction_hash,
)


class WithdrawalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.withdrawals = WithdrawalRepository(session)
        self.wallets = WalletRepository(session)
        self.transactions = TransactionRepository(session)

    async def request_withdrawal(
        self,
        *,
        user_id,
        amount: Decimal,
        fee: Decimal,
        destination_address: str,
        idempotency_key: str,
        asset: str = "USDT",
        network: str = "BSC",
    ) -> Withdrawal:
        amount = parse_positive_amount(amount)
        fee = parse_nonnegative_amount(fee)
        destination_address = validate_bsc_address(destination_address)
        idempotency_key = validate_idempotency_key(idempotency_key)

        existing = await self.withdrawals.get_by_idempotency_key(
            idempotency_key, for_update=True
        )
        if existing is not None:
            if (
                existing.user_id != user_id
                or existing.amount != amount
                or existing.destination_address != destination_address
            ):
                raise ValueError(
                    "Idempotency key is already bound to a different withdrawal."
                )
            return existing

        wallet = await self.wallets.get_by_user_and_asset(
            user_id, asset, for_update=True
        )
        if wallet is None or wallet.status.value != "active":
            raise ValueError("Active wallet not found.")
        total_debit = amount + fee
        if wallet.available_balance < total_debit:
            raise ValueError("Insufficient available balance.")

        before = wallet.available_balance
        after = before - total_debit
        wallet.available_balance = after
        wallet.reserved_balance += total_debit
        wallet.version += 1

        withdrawal = Withdrawal(
            user_id=user_id,
            wallet_id=wallet.id,
            network=network,
            asset=asset,
            destination_address=destination_address,
            amount=amount,
            fee=fee,
            status=WithdrawalStatus.REQUESTED,
            idempotency_key=idempotency_key,
        )
        await self.withdrawals.add(withdrawal)
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.PENDING,
            asset=asset,
            amount=total_debit,
            balance_before=before,
            balance_after=after,
            reference_type="withdrawal",
            reference_id=withdrawal.id,
            idempotency_key=f"withdrawal-debit:{idempotency_key}",
            extra_data={"fee": str(fee), "destination_address": destination_address},
        )
        await self.transactions.add(transaction)
        await self.session.flush()
        return withdrawal

    async def mark_processing(self, withdrawal_id) -> Withdrawal:
        withdrawal = await self.withdrawals.get_for_update(withdrawal_id)
        if withdrawal.status not in {
            WithdrawalStatus.REQUESTED,
            WithdrawalStatus.APPROVED,
        }:
            raise ValueError("Withdrawal is not ready for processing.")
        withdrawal.status = WithdrawalStatus.PROCESSING
        withdrawal.version += 1
        await self.session.flush()
        return withdrawal

    async def mark_completed(self, withdrawal_id, tx_hash: str) -> Withdrawal:
        tx_hash = validate_transaction_hash(tx_hash)
        withdrawal = await self.withdrawals.get_for_update(withdrawal_id)
        if withdrawal.status == WithdrawalStatus.COMPLETED:
            if withdrawal.tx_hash != tx_hash:
                raise ValueError(
                    "Completed withdrawal cannot be assigned another transaction hash."
                )
            return withdrawal
        if withdrawal.status not in {
            WithdrawalStatus.REQUESTED,
            WithdrawalStatus.APPROVED,
            WithdrawalStatus.PROCESSING,
        }:
            raise ValueError("Withdrawal cannot be completed from its current state.")

        wallet = await self.wallets.get_active_for_update(withdrawal.wallet_id)
        total_debit = withdrawal.amount + withdrawal.fee
        if wallet.reserved_balance < total_debit:
            raise RuntimeError(
                "Reserved balance is smaller than the withdrawal amount."
            )
        wallet.reserved_balance -= total_debit
        wallet.version += 1

        ledger = await self.transactions.get_by_idempotency_key(
            f"withdrawal-debit:{withdrawal.idempotency_key}", for_update=True
        )
        if ledger is None:
            raise RuntimeError("Withdrawal ledger entry is missing.")
        ledger.status = TransactionStatus.POSTED
        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.tx_hash = tx_hash
        withdrawal.processed_at = datetime.now(timezone.utc)
        withdrawal.version += 1
        await self.session.flush()
        return withdrawal

    async def mark_failed(self, withdrawal_id, reason: str) -> Withdrawal:
        withdrawal = await self.withdrawals.get_for_update(withdrawal_id)
        if withdrawal.status in {
            WithdrawalStatus.COMPLETED,
            WithdrawalStatus.CANCELLED,
        }:
            return withdrawal
        wallet = await self.wallets.get_active_for_update(withdrawal.wallet_id)
        total_debit = withdrawal.amount + withdrawal.fee
        if wallet.reserved_balance < total_debit:
            raise RuntimeError(
                "Reserved balance is smaller than the withdrawal amount."
            )
        wallet.reserved_balance -= total_debit
        wallet.available_balance += total_debit
        wallet.version += 1

        ledger = await self.transactions.get_by_idempotency_key(
            f"withdrawal-debit:{withdrawal.idempotency_key}", for_update=True
        )
        if ledger is not None:
            ledger.status = TransactionStatus.VOIDED
        withdrawal.status = WithdrawalStatus.FAILED
        withdrawal.failure_reason = reason[:1000]
        withdrawal.processed_at = datetime.now(timezone.utc)
        withdrawal.version += 1
        await self.session.flush()
        return withdrawal
