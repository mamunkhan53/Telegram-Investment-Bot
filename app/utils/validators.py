from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from web3 import Web3

from app.config.constants import MONEY_PRECISION, TX_HASH_LENGTH, WALLET_ADDRESS_LENGTH

_IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TX_HASH_PATTERN = re.compile(r"^0x[a-fA-F0-9]{64}$")


def parse_positive_amount(
    value: str | Decimal, *, maximum: Decimal | None = None
) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Amount must be a valid decimal number.") from exc

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if -amount.as_tuple().exponent > MONEY_PRECISION:
        raise ValueError(f"Amount supports at most {MONEY_PRECISION} decimal places.")
    if maximum is not None and amount > maximum:
        raise ValueError("Amount exceeds the allowed maximum.")
    return amount


def parse_nonnegative_amount(value: str | Decimal) -> Decimal:
    amount = Decimal(str(value).strip())
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amount must be zero or greater.")
    if -amount.as_tuple().exponent > MONEY_PRECISION:
        raise ValueError(f"Amount supports at most {MONEY_PRECISION} decimal places.")
    return amount


def validate_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not _IDEMPOTENCY_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Idempotency key contains unsupported characters or is too long."
        )
    return normalized


def validate_bsc_address(value: str) -> str:
    normalized = value.strip()
    if len(normalized) != WALLET_ADDRESS_LENGTH or not Web3.is_address(normalized):
        raise ValueError("Invalid BNB Smart Chain wallet address.")
    return Web3.to_checksum_address(normalized)


def validate_transaction_hash(value: str) -> str:
    normalized = value.strip()
    if len(normalized) != TX_HASH_LENGTH or not _TX_HASH_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid blockchain transaction hash.")
    return normalized.lower()
