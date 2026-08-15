from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base, TimestampMixin
from app.database.models.enums import TransactionStatus, TransactionType


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transactions_idempotency_key"),
        CheckConstraint("amount >= 0", name="ck_transactions_amount_nonnegative"),
        Index("ix_transactions_wallet_created_at", "wallet_id", "created_at"),
        Index(
            "ix_transactions_user_type_created_at",
            "user_id",
            "transaction_type",
            "created_at",
        ),
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
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(
            TransactionType,
            name="transaction_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ), 
        nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(
            TransactionStatus,
            name="transaction_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=TransactionStatus.POSTED,
        server_default=TransactionStatus.POSTED.value,
    )
    asset: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USDT", server_default="USDT"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    external_reference: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict, server_default="{}"
    )
