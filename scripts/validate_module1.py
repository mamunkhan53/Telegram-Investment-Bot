from app.config.settings import Settings
from app.database.base import Base


def main() -> None:
    settings = Settings(
        app_env="testing", secret_key="x" * 32, admin_session_secret="y" * 32
    )
    assert settings.bsc_chain_id == 56
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
    print("settings and metadata import: ok")
    print("tables:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    main()
