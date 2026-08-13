from decimal import Decimal

import pytest

from app.utils.validators import (
    parse_nonnegative_amount,
    parse_positive_amount,
    validate_bsc_address,
    validate_idempotency_key,
    validate_transaction_hash,
)


def test_parse_positive_amount_accepts_decimal() -> None:
    assert parse_positive_amount("10.250") == Decimal("10.250")


def test_parse_positive_amount_rejects_zero() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        parse_positive_amount("0")


def test_parse_nonnegative_amount_accepts_zero() -> None:
    assert parse_nonnegative_amount("0") == Decimal(0)


def test_validate_idempotency_key_rejects_spaces() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        validate_idempotency_key("invalid key")


def test_validate_bsc_address_returns_checksum_address() -> None:
    address = "0x000000000000000000000000000000000000dead"
    assert validate_bsc_address(address).startswith("0x")


def test_validate_transaction_hash_normalizes_case() -> None:
    tx_hash = "0x" + "AB" * 32
    assert validate_transaction_hash(tx_hash) == tx_hash.lower()
