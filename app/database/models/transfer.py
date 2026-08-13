from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base, TimestampMixin, VersionedMixin
from app.database.models.enums import DepositStatus, WithdrawalStatus


class Deposit(TimestampMixin, Base):
    __tablename__ = "deposits"
    __table_args__ = (
        UniqueConstraint(
            "network", "tx_hash", "log_index", name="uq_deposits_chain_event"
        ),
        CheckConstraint("amount > 0", name="ck_deposits_amount_positive"),
        Index("ix_deposits_status_detected_at", "status", "detected_at"),
        Index("ix_deposits_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    network: Mapped[str] = mapped_column(
        String(32), nullable=False, default="BSC", server_default="BSC"
    )
    asset: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USDT", server_default="USDT"
    )
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    log_index: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    from_address: Mapped[str | None] = mapped_column(String(128))
    to_address: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    block_number: Mapped[int | None] = mapped_column()
    confirmations: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    status: Mapped[DepositStatus] = mapped_column(
        SQLEnum(DepositStatus, name="deposit_status"),
        nullable=False,
        default=DepositStatus.DETECTED,
        server_default=DepositStatus.DETECTED.value,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict, server_default="{}"
    )


class Withdrawal(TimestampMixin, VersionedMixin, Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_withdrawals_idempotency_key"),
        CheckConstraint("amount > 0", name="ck_withdrawals_amount_positive"),
        CheckConstraint("fee >= 0", name="ck_withdrawals_fee_nonnegative"),
        Index("ix_withdrawals_status_requested_at", "status", "requested_at"),
        Index("ix_withdrawals_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    network: Mapped[str] = mapped_column(
        String(32), nullable=False, default="BSC", server_default="BSC"
    )
    asset: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USDT", server_default="USDT"
    )
    destination_address: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    fee: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=Decimal(0), server_default="0"
    )
    status: Mapped[WithdrawalStatus] = mapped_column(
        SQLEnum(WithdrawalStatus, name="withdrawal_status"),
        nullable=False,
        default=WithdrawalStatus.REQUESTED,
        server_default=WithdrawalStatus.REQUESTED.value,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(66), unique=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict, server_default="{}"
    )
