from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "telegram-investment-platform"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: SecretStr = Field(default=SecretStr("change-me-change-me"))

    telegram_bot_token: SecretStr | None = Field(
    default=None,
    validation_alias="TELEGRAM_BOT_TOKEN",
    )
    telegram_webhook_url: str | None = None
    telegram_webhook_secret: SecretStr | None = None

    database_url: str = (
        "postgresql+asyncpg://investment:investment@localhost:5432/investment"
    )
    database_sync_url: str = (
        "postgresql+psycopg://investment:investment@localhost:5432/investment"
    )

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True

    admin_username: str = "admin"
    admin_password_hash: SecretStr | None = None
    admin_session_secret: SecretStr = Field(
        default=SecretStr("change-admin-session-secret")
    )

    bsc_rpc_url: str = "https://bsc-dataseed.binance.org/"
    bsc_chain_id: int = 56
    bsc_usdt_contract_address: str | None = None
    bsc_confirmations_required: int = Field(default=12, ge=1, le=200)
    bsc_scan_api_key: SecretStr | None = None
    platform_deposit_address: str | None = None
    platform_hot_wallet_address: str | None = None
    platform_hot_wallet_private_key: SecretStr | None = None

    admin_base_url: str = "http://localhost:8000"
    public_base_url: str = "http://localhost:8000"

    scheduler_enabled: bool = True
    deposit_check_interval_seconds: int = Field(default=30, ge=5)
    investment_tick_interval_seconds: int = Field(default=60, ge=10)
    withdrawal_check_interval_seconds: int = Field(default=60, ge=10)
    notification_check_interval_seconds: int = Field(default=60, ge=10)

    sentry_dsn: str | None = None

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        normalized = str(value).lower().strip()
        aliases = {"dev": "development", "test": "testing", "prod": "production"}
        return aliases.get(normalized, normalized)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper().strip()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("bsc_chain_id")
    @classmethod
    def validate_chain_id(cls, value: int) -> int:
        if value != 56:
            raise ValueError(
                "This release supports BNB Smart Chain mainnet only (chain ID 56)."
            )
        return value

    def validate_runtime_configuration(self) -> None:
        """Fail fast for settings required outside local scaffold/testing runs."""
        if self.app_env in {"staging", "production"}:
            required = {
                "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
                "ADMIN_PASSWORD_HASH": self.admin_password_hash,
                "BSC_USDT_CONTRACT_ADDRESS": self.bsc_usdt_contract_address,
                "PLATFORM_DEPOSIT_ADDRESS": self.platform_deposit_address,
            }
            missing = [
                name
                for name, value in required.items()
                if value is None or not str(value).strip()
            ]
            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )

            if len(
                self.secret_key.get_secret_value()
            ) < 32 or self.secret_key.get_secret_value().startswith("change-"):
                raise ValueError(
                    "SECRET_KEY must be replaced with a random value of at least 32 characters outside development/testing."
                )
            if len(
                self.admin_session_secret.get_secret_value()
            ) < 32 or self.admin_session_secret.get_secret_value().startswith(
                "change-"
            ):
                raise ValueError(
                    "ADMIN_SESSION_SECRET must be replaced with a random value of at least 32 characters outside development/testing."
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_configuration()
    return settings
