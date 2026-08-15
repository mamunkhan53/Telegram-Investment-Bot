from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
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

from app.database.base import Base, TimestampMixin, VersionedMixin
from app.database.models.enums import WalletStatus


class Wallet(TimestampMixin, VersionedMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "asset", name="uq_wallets_user_asset"),
        CheckConstraint(
            "available_balance >= 0", name="ck_wallets_available_balance_nonnegative"
        ),
        CheckConstraint(
            "reserved_balance >= 0", name="ck_wallets_reserved_balance_nonnegative"
        ),
        Index("ix_wallets_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USDT", server_default="USDT"
    )
    network: Mapped[str] = mapped_column(
        String(32), nullable=False, default="BSC", server_default="BSC"
    )
    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=Decimal(0), server_default="0"
    )
    reserved_balance: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=Decimal(0), server_default="0"
    )
    deposit_address: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[WalletStatus] = mapped_column(
        SQLEnum(
            WalletStatus,
            name="wallet_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=WalletStatus.ACTIVE,
        server_default=WalletStatus.ACTIVE.value,
    )
