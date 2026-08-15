from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base, TimestampMixin, VersionedMixin
from app.database.models.enums import InvestmentStatus, PlanStatus


class InvestmentPlan(TimestampMixin, Base):
    __tablename__ = "investment_plans"
    __table_args__ = (
        CheckConstraint(
            "minimum_amount > 0", name="ck_investment_plans_minimum_positive"
        ),
        CheckConstraint(
            "maximum_amount IS NULL OR maximum_amount >= minimum_amount",
            name="ck_investment_plans_amount_range",
        ),
        CheckConstraint(
            "duration_days > 0", name="ck_investment_plans_duration_positive"
        ),
        CheckConstraint(
            "profit_rate >= 0", name="ck_investment_plans_profit_nonnegative"
        ),
        Index("ix_investment_plans_status_sort_order", "status", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    asset: Mapped[str] = mapped_column(
        String(16), nullable=False, default="USDT", server_default="USDT"
    )
    network: Mapped[str] = mapped_column(
        String(32), nullable=False, default="BSC", server_default="BSC"
    )
    minimum_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    maximum_amount: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    auto_reinvest_allowed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    status: Mapped[PlanStatus] = mapped_column(
        SQLEnum(
        PlanStatus,
        name="plan_status",
        values_callable=lambda enum_class: [member.value for member in enum_class],
    ),
        nullable=False,
        default=PlanStatus.DRAFT,
        server_default=PlanStatus.DRAFT.value,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class Investment(TimestampMixin, VersionedMixin, Base):
    __tablename__ = "investments"
    __table_args__ = (
        CheckConstraint(
            "principal_amount > 0", name="ck_investments_principal_positive"
        ),
        CheckConstraint("profit_amount >= 0", name="ck_investments_profit_nonnegative"),
        CheckConstraint(
            "paid_profit_amount >= 0", name="ck_investments_paid_profit_nonnegative"
        ),
        Index("ix_investments_user_status", "user_id", "status"),
        Index("ix_investments_next_accrual_at", "next_accrual_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investment_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    profit_amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=Decimal(0), server_default="0"
    )
    paid_profit_amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 18), nullable=False, default=Decimal(0), server_default="0"
    )
    status: Mapped[InvestmentStatus] = mapped_column(
        SQLEnum(
        InvestmentStatus,
        name="investment_status",
        values_callable=lambda enum_class: [member.value for member in enum_class],
    ),
        nullable=False,
        default=InvestmentStatus.PENDING,
        server_default=InvestmentStatus.PENDING.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    maturity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_accrual_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_reinvest: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
