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
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base, TimestampMixin
from app.database.models.enums import ReferralStatus


class ReferralReward(TimestampMixin, Base):
    __tablename__ = "referral_rewards"
    __table_args__ = (
        UniqueConstraint(
            "referrer_id",
            "referred_user_id",
            "source_investment_id",
            name="uq_referral_reward_source",
        ),
        CheckConstraint("level > 0", name="ck_referral_rewards_level_positive"),
        CheckConstraint(
            "reward_percent >= 0", name="ck_referral_rewards_percent_nonnegative"
        ),
        CheckConstraint(
            "reward_amount >= 0", name="ck_referral_rewards_amount_nonnegative"
        ),
        Index("ix_referral_rewards_referrer_status", "referrer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    referred_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    source_investment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investments.id", ondelete="SET NULL")
    )
    level: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    reward_percent: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    status: Mapped[ReferralStatus] = mapped_column(
        SQLEnum(
            ReferralStatus,
            name="referral_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=ReferralStatus.PENDING,
        server_default=ReferralStatus.PENDING.value,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created_at", "actor_user_id", "created_at"),
        Index(
            "ix_audit_logs_entity_created_at", "entity_type", "entity_id", "created_at"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
