from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.config.settings import Settings
from app.database.base import Base
from app.database.models import (
    DepositStatus,
    InvestmentStatus,
    TransactionType,
    UserStatus,
)


def test_settings_normalize_log_level() -> None:
    settings = Settings(
        log_level="debug",
        app_env="testing",
        secret_key="x" * 32,
        admin_session_secret="y" * 32,
    )
    assert settings.log_level == "DEBUG"


def test_settings_reject_unsupported_chain() -> None:
    with pytest.raises(ValidationError):
        Settings(
            bsc_chain_id=1,
            app_env="testing",
            secret_key="x" * 32,
            admin_session_secret="y" * 32,
        )


def test_production_settings_require_operational_values() -> None:
    settings = Settings(
        app_env="production", secret_key="x" * 32, admin_session_secret="y" * 32
    )
    with pytest.raises(ValueError, match="Missing required production settings"):
        settings.validate_runtime_configuration()


def test_core_tables_are_registered() -> None:
    expected = {
        "users",
        "wallets",
        "investment_plans",
        "investments",
        "deposits",
        "withdrawals",
        "transactions",
        "referral_rewards",
        "audit_logs",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_financial_enums_are_stable_strings() -> None:
    assert UserStatus.ACTIVE.value == "active"
    assert DepositStatus.CREDITED.value == "credited"
    assert InvestmentStatus.COMPLETED.value == "completed"
    assert TransactionType.REFERRAL_REWARD.value == "referral_reward"
    assert Decimal("1.00") > Decimal(0)
