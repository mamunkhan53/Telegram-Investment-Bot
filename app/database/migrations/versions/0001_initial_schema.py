"""Initial investment platform schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # PostgreSQL ENUM definitions
    #
    # create_type=False is important here because we create the ENUM
    # types explicitly below. This prevents SQLAlchemy from attempting
    # to create them again during op.create_table().
    # ------------------------------------------------------------------

    user_status = sa.Enum(
        "active",
        "suspended",
        "banned",
        name="user_status",
        create_type=False,
    )

    wallet_status = sa.Enum(
        "active",
        "frozen",
        "closed",
        name="wallet_status",
        create_type=False,
    )

    plan_status = sa.Enum(
        "draft",
        "active",
        "paused",
        "archived",
        name="plan_status",
        create_type=False,
    )

    investment_status = sa.Enum(
        "pending",
        "active",
        "completed",
        "cancelled",
        name="investment_status",
        create_type=False,
    )

    deposit_status = sa.Enum(
        "detected",
        "confirmed",
        "credited",
        "rejected",
        name="deposit_status",
        create_type=False,
    )

    withdrawal_status = sa.Enum(
        "requested",
        "approved",
        "processing",
        "completed",
        "failed",
        "cancelled",
        name="withdrawal_status",
        create_type=False,
    )

    transaction_type = sa.Enum(
        "deposit",
        "withdrawal",
        "investment",
        "profit",
        "referral_reward",
        "reinvestment",
        "fee",
        "adjustment",
        name="transaction_type",
        create_type=False,
    )

    transaction_status = sa.Enum(
        "pending",
        "posted",
        "voided",
        name="transaction_status",
        create_type=False,
    )

    referral_status = sa.Enum(
        "pending",
        "paid",
        "reversed",
        name="referral_status",
        create_type=False,
    )

    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Prevent two Alembic processes from creating the same ENUM types
    # at the same time.
    # ------------------------------------------------------------------

    bind.execute(sa.text("SELECT pg_advisory_xact_lock(918273645)"))

    # ------------------------------------------------------------------
    # Create ENUM types safely.
    #
    # PostgreSQL does not support CREATE TYPE ... IF NOT EXISTS directly
    # on all supported versions, so use a DO block with a catalog check.
    # ------------------------------------------------------------------

    enum_definitions = [
        (
            "user_status",
            ["active", "suspended", "banned"],
        ),
        (
            "wallet_status",
            ["active", "frozen", "closed"],
        ),
        (
            "plan_status",
            ["draft", "active", "paused", "archived"],
        ),
        (
            "investment_status",
            ["pending", "active", "completed", "cancelled"],
        ),
        (
            "deposit_status",
            ["detected", "confirmed", "credited", "rejected"],
        ),
        (
            "withdrawal_status",
            [
                "requested",
                "approved",
                "processing",
                "completed",
                "failed",
                "cancelled",
            ],
        ),
        (
            "transaction_type",
            [
                "deposit",
                "withdrawal",
                "investment",
                "profit",
                "referral_reward",
                "reinvestment",
                "fee",
                "adjustment",
            ],
        ),
        (
            "transaction_status",
            ["pending", "posted", "voided"],
        ),
        (
            "referral_status",
            ["pending", "paid", "reversed"],
        ),
    ]

    for enum_name, values in enum_definitions:
        values_sql = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in values
        )

        bind.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_type t
                        JOIN pg_namespace n
                            ON n.oid = t.typnamespace
                        WHERE t.typname = '{enum_name}'
                          AND n.nspname = 'public'
                    ) THEN
                        CREATE TYPE public."{enum_name}"
                        AS ENUM ({values_sql});
                    END IF;
                END
                $$;
                """
            )
        )

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("referral_code", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column(
            "language_code",
            sa.String(length=10),
            server_default="en",
            nullable=False,
        ),
        sa.Column(
            "status",
            user_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("referred_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "suspended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["referred_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_user_id",
            name="uq_users_telegram_user_id",
        ),
        sa.UniqueConstraint("referral_code"),
    )

    op.create_index(
        "ix_users_status_created_at",
        "users",
        ["status", "created_at"],
    )

    op.create_index(
        "ix_users_referred_by_id",
        "users",
        ["referred_by_id"],
    )

    # ------------------------------------------------------------------
    # INVESTMENT PLANS
    # ------------------------------------------------------------------

    op.create_table(
        "investment_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "asset",
            sa.String(length=16),
            server_default="USDT",
            nullable=False,
        ),
        sa.Column(
            "network",
            sa.String(length=32),
            server_default="BSC",
            nullable=False,
        ),
        sa.Column(
            "minimum_amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "maximum_amount",
            sa.Numeric(38, 18),
            nullable=True,
        ),
        sa.Column(
            "duration_days",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "profit_rate",
            sa.Numeric(12, 8),
            nullable=False,
        ),
        sa.Column(
            "auto_reinvest_allowed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "status",
            plan_status,
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "minimum_amount > 0",
            name="ck_investment_plans_minimum_positive",
        ),
        sa.CheckConstraint(
            "maximum_amount IS NULL OR maximum_amount >= minimum_amount",
            name="ck_investment_plans_amount_range",
        ),
        sa.CheckConstraint(
            "duration_days > 0",
            name="ck_investment_plans_duration_positive",
        ),
        sa.CheckConstraint(
            "profit_rate >= 0",
            name="ck_investment_plans_profit_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_index(
        "ix_investment_plans_status_sort_order",
        "investment_plans",
        ["status", "sort_order"],
    )

    # ------------------------------------------------------------------
    # WALLETS
    # ------------------------------------------------------------------

    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "asset",
            sa.String(length=16),
            server_default="USDT",
            nullable=False,
        ),
        sa.Column(
            "network",
            sa.String(length=32),
            server_default="BSC",
            nullable=False,
        ),
        sa.Column(
            "available_balance",
            sa.Numeric(38, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "reserved_balance",
            sa.Numeric(38, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "deposit_address",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "status",
            wallet_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "available_balance >= 0",
            name="ck_wallets_available_balance_nonnegative",
        ),
        sa.CheckConstraint(
            "reserved_balance >= 0",
            name="ck_wallets_reserved_balance_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "asset",
            name="uq_wallets_user_asset",
        ),
    )

    op.create_index(
        "ix_wallets_user_status",
        "wallets",
        ["user_id", "status"],
    )

    # ------------------------------------------------------------------
    # INVESTMENTS
    # ------------------------------------------------------------------

    op.create_table(
        "investments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column(
            "principal_amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "profit_amount",
            sa.Numeric(38, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "paid_profit_amount",
            sa.Numeric(38, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            investment_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "maturity_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "next_accrual_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "auto_reinvest",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "principal_amount > 0",
            name="ck_investments_principal_positive",
        ),
        sa.CheckConstraint(
            "profit_amount >= 0",
            name="ck_investments_profit_nonnegative",
        ),
        sa.CheckConstraint(
            "paid_profit_amount >= 0",
            name="ck_investments_paid_profit_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["investment_plans.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_investments_user_status",
        "investments",
        ["user_id", "status"],
    )

    op.create_index(
        "ix_investments_next_accrual_at",
        "investments",
        ["next_accrual_at"],
    )

    # ------------------------------------------------------------------
    # DEPOSITS
    # ------------------------------------------------------------------

    op.create_table(
        "deposits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "network",
            sa.String(length=32),
            server_default="BSC",
            nullable=False,
        ),
        sa.Column(
            "asset",
            sa.String(length=16),
            server_default="USDT",
            nullable=False,
        ),
        sa.Column(
            "tx_hash",
            sa.String(length=66),
            nullable=False,
        ),
        sa.Column(
            "log_index",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "from_address",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "to_address",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "block_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "confirmations",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            deposit_status,
            server_default="detected",
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "credited_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_deposits_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "network",
            "tx_hash",
            "log_index",
            name="uq_deposits_chain_event",
        ),
    )

    op.create_index(
        "ix_deposits_status_detected_at",
        "deposits",
        ["status", "detected_at"],
    )

    op.create_index(
        "ix_deposits_user_status",
        "deposits",
        ["user_id", "status"],
    )

    # ------------------------------------------------------------------
    # WITHDRAWALS
    # ------------------------------------------------------------------

    op.create_table(
        "withdrawals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "network",
            sa.String(length=32),
            server_default="BSC",
            nullable=False,
        ),
        sa.Column(
            "asset",
            sa.String(length=16),
            server_default="USDT",
            nullable=False,
        ),
        sa.Column(
            "destination_address",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "fee",
            sa.Numeric(38, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            withdrawal_status,
            server_default="requested",
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "tx_hash",
            sa.String(length=66),
            nullable=True,
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failure_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_withdrawals_amount_positive",
        ),
        sa.CheckConstraint(
            "fee >= 0",
            name="ck_withdrawals_fee_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_withdrawals_idempotency_key",
        ),
        sa.UniqueConstraint("tx_hash"),
    )

    op.create_index(
        "ix_withdrawals_status_requested_at",
        "withdrawals",
        ["status", "requested_at"],
    )

    op.create_index(
        "ix_withdrawals_user_status",
        "withdrawals",
        ["user_id", "status"],
    )

    # ------------------------------------------------------------------
    # TRANSACTIONS
    # ------------------------------------------------------------------

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transaction_type",
            transaction_type,
            nullable=False,
        ),
        sa.Column(
            "status",
            transaction_status,
            server_default="posted",
            nullable=False,
        ),
        sa.Column(
            "asset",
            sa.String(length=16),
            server_default="USDT",
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "balance_before",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "reference_type",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "reference_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "external_reference",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_transactions_amount_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_transactions_idempotency_key",
        ),
    )

    op.create_index(
        "ix_transactions_wallet_created_at",
        "transactions",
        ["wallet_id", "created_at"],
    )

    op.create_index(
        "ix_transactions_user_type_created_at",
        "transactions",
        ["user_id", "transaction_type", "created_at"],
    )

    # ------------------------------------------------------------------
    # REFERRAL REWARDS
    # ------------------------------------------------------------------

    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referrer_id", sa.Uuid(), nullable=False),
        sa.Column("referred_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_investment_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "level",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "reward_percent",
            sa.Numeric(12, 8),
            nullable=False,
        ),
        sa.Column(
            "reward_amount",
            sa.Numeric(38, 18),
            nullable=False,
        ),
        sa.Column(
            "status",
            referral_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "level > 0",
            name="ck_referral_rewards_level_positive",
        ),
        sa.CheckConstraint(
            "reward_percent >= 0",
            name="ck_referral_rewards_percent_nonnegative",
        ),
        sa.CheckConstraint(
            "reward_amount >= 0",
            name="ck_referral_rewards_amount_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["referrer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["referred_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_investment_id"],
            ["investments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "referrer_id",
            "referred_user_id",
            "source_investment_id",
            name="uq_referral_reward_source",
        ),
    )

    op.create_index(
        "ix_referral_rewards_referrer_status",
        "referral_rewards",
        ["referrer_id", "status"],
    )

    # ------------------------------------------------------------------
    # AUDIT LOGS
    # ------------------------------------------------------------------

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "ip_address",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_audit_logs_actor_created_at",
        "audit_logs",
        ["actor_user_id", "created_at"],
    )

    op.create_index(
        "ix_audit_logs_entity_created_at",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # BLOCKCHAIN SCAN STATES
    # ------------------------------------------------------------------

    op.create_table(
        "blockchain_scan_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "network",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "asset",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "deposit_address",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "last_scanned_block",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint([], []),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "network",
            "asset",
            "deposit_address",
            name="uq_blockchain_scan_scope",
        ),
    )

    op.create_index(
        "ix_blockchain_scan_states_next_block",
        "blockchain_scan_states",
        ["network", "asset", "last_scanned_block"],
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Drop tables and indexes in reverse dependency order.
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_blockchain_scan_states_next_block",
        table_name="blockchain_scan_states",
    )
    op.drop_table("blockchain_scan_states")

    op.drop_index(
        "ix_audit_logs_entity_created_at",
        table_name="audit_logs",
    )
    op.drop_index(
        "ix_audit_logs_actor_created_at",
        table_name="audit_logs",
    )
    op.drop_table("audit_logs")

    op.drop_index(
        "ix_referral_rewards_referrer_status",
        table_name="referral_rewards",
    )
    op.drop_table("referral_rewards")

    op.drop_index(
        "ix_transactions_user_type_created_at",
        table_name="transactions",
    )
    op.drop_index(
        "ix_transactions_wallet_created_at",
        table_name="transactions",
    )
    op.drop_table("transactions")

    op.drop_index(
        "ix_withdrawals_user_status",
        table_name="withdrawals",
    )
    op.drop_index(
        "ix_withdrawals_status_requested_at",
        table_name="withdrawals",
    )
    op.drop_table("withdrawals")

    op.drop_index(
        "ix_deposits_user_status",
        table_name="deposits",
    )
    op.drop_index(
        "ix_deposits_status_detected_at",
        table_name="deposits",
    )
    op.drop_table("deposits")

    op.drop_index(
        "ix_investments_next_accrual_at",
        table_name="investments",
    )
    op.drop_index(
        "ix_investments_user_status",
        table_name="investments",
    )
    op.drop_table("investments")

    op.drop_index(
        "ix_wallets_user_status",
        table_name="wallets",
    )
    op.drop_table("wallets")

    op.drop_index(
        "ix_investment_plans_status_sort_order",
        table_name="investment_plans",
    )
    op.drop_table("investment_plans")

    op.drop_index(
        "ix_users_referred_by_id",
        table_name="users",
    )
    op.drop_index(
        "ix_users_status_created_at",
        table_name="users",
    )
    op.drop_table("users")

    # ------------------------------------------------------------------
    # Drop ENUM types.
    # ------------------------------------------------------------------

    bind = op.get_bind()

    bind.execute(sa.text("SELECT pg_advisory_xact_lock(918273645)"))

    for type_name in (
        "referral_status",
        "transaction_status",
        "transaction_type",
        "withdrawal_status",
        "deposit_status",
        "investment_status",
        "plan_status",
        "wallet_status",
        "user_status",
    ):
        bind.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_type t
                        JOIN pg_namespace n
                            ON n.oid = t.typnamespace
                        WHERE t.typname = '{type_name}'
                          AND n.nspname = 'public'
                    ) THEN
                        DROP TYPE public."{type_name}";
                    END IF;
                END
                $$;
                """
            )
        )
