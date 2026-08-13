from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"


class WalletStatus(StrEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class InvestmentStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DepositStatus(StrEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    CREDITED = "credited"
    REJECTED = "rejected"


class WithdrawalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INVESTMENT = "investment"
    PROFIT = "profit"
    REFERRAL_REWARD = "referral_reward"
    REINVESTMENT = "reinvestment"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    POSTED = "posted"
    VOIDED = "voided"


class ReferralStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    REVERSED = "reversed"
