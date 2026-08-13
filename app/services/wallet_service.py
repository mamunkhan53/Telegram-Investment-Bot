from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction
from app.database.models.enums import TransactionStatus, TransactionType
from app.database.repositories.ledger_repository import TransactionRepository
from app.database.repositories.wallet_repository import WalletRepository
from app.utils.validators import parse_positive_amount, validate_idempotency_key


class IdempotencyConflictError(ValueError):
    """Raised when one idempotency key is reused for a different operation."""


class InsufficientBalanceError(ValueError):
    """Raised when a wallet cannot cover a requested debit or reservation."""


class WalletService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.wallets = WalletRepository(session)
        self.transactions = TransactionRepository(session)

    async def credit(
        self,
        *,
        wallet_id,
        user_id,
        amount: Decimal,
        transaction_type: TransactionType,
        idempotency_key: str,
        reference_type: str | None = None,
        reference_id=None,
        external_reference: str | None = None,
        extra_data: dict | None = None,
    ) -> Transaction:
        amount = parse_positive_amount(amount)
        idempotency_key = validate_idempotency_key(idempotency_key)
        existing = await self.transactions.get_by_idempotency_key(
            idempotency_key, for_update=True
        )
        if existing is not None:
            self._assert_same_operation(existing, wallet_id, amount, transaction_type)
            return existing

        wallet = await self.wallets.get_active_for_update(wallet_id)
        if wallet.user_id != user_id:
            raise ValueError("Wallet does not belong to the user.")
        before = wallet.available_balance
        after = before + amount
        wallet.available_balance = after
        wallet.version += 1
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            status=TransactionStatus.POSTED,
            amount=amount,
            balance_before=before,
            balance_after=after,
            reference_type=reference_type,
            reference_id=reference_id,
            external_reference=external_reference,
            idempotency_key=idempotency_key,
            extra_data=extra_data or {},
        )
        return await self.transactions.add(transaction)

    async def debit(
        self,
        *,
        wallet_id,
        user_id,
        amount: Decimal,
        transaction_type: TransactionType,
        idempotency_key: str,
        reference_type: str | None = None,
        reference_id=None,
        external_reference: str | None = None,
        extra_data: dict | None = None,
    ) -> Transaction:
        amount = parse_positive_amount(amount)
        idempotency_key = validate_idempotency_key(idempotency_key)
        existing = await self.transactions.get_by_idempotency_key(
            idempotency_key, for_update=True
        )
        if existing is not None:
            self._assert_same_operation(existing, wallet_id, amount, transaction_type)
            return existing

        wallet = await self.wallets.get_active_for_update(wallet_id)
        if wallet.user_id != user_id:
            raise ValueError("Wallet does not belong to the user.")
        if wallet.available_balance < amount:
            raise InsufficientBalanceError("Insufficient available balance.")
        before = wallet.available_balance
        after = before - amount
        wallet.available_balance = after
        wallet.version += 1
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            status=TransactionStatus.POSTED,
            amount=amount,
            balance_before=before,
            balance_after=after,
            reference_type=reference_type,
            reference_id=reference_id,
            external_reference=external_reference,
            idempotency_key=idempotency_key,
            extra_data=extra_data or {},
        )
        return await self.transactions.add(transaction)

    async def reserve(self, *, wallet_id, user_id, amount: Decimal) -> None:
        amount = parse_positive_amount(amount)
        wallet = await self.wallets.get_active_for_update(wallet_id)
        if wallet.user_id != user_id:
            raise ValueError("Wallet does not belong to the user.")
        if wallet.available_balance < amount:
            raise InsufficientBalanceError("Insufficient available balance.")
        wallet.available_balance -= amount
        wallet.reserved_balance += amount
        wallet.version += 1
        await self.session.flush()

    async def release_reservation(self, *, wallet_id, user_id, amount: Decimal) -> None:
        amount = parse_positive_amount(amount)
        wallet = await self.wallets.get_active_for_update(wallet_id)
        if wallet.user_id != user_id:
            raise ValueError("Wallet does not belong to the user.")
        if wallet.reserved_balance < amount:
            raise ValueError("Reserved balance is smaller than the requested release.")
        wallet.reserved_balance -= amount
        wallet.available_balance += amount
        wallet.version += 1
        await self.session.flush()

    async def consume_reservation(self, *, wallet_id, user_id, amount: Decimal) -> None:
        amount = parse_positive_amount(amount)
        wallet = await self.wallets.get_active_for_update(wallet_id)
        if wallet.user_id != user_id:
            raise ValueError("Wallet does not belong to the user.")
        if wallet.reserved_balance < amount:
            raise ValueError(
                "Reserved balance is smaller than the requested consumption."
            )
        wallet.reserved_balance -= amount
        wallet.version += 1
        await self.session.flush()

    @staticmethod
    def _assert_same_operation(
        existing: Transaction,
        wallet_id,
        amount: Decimal,
        transaction_type: TransactionType,
    ) -> None:
        if (
            existing.wallet_id != wallet_id
            or existing.amount != amount
            or existing.transaction_type != transaction_type
        ):
            raise IdempotencyConflictError(
                "Idempotency key is already bound to a different operation."
            )
