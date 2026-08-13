from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TokenTransfer:
    network: str
    asset: str
    tx_hash: str
    log_index: int
    from_address: str
    to_address: str
    amount: Decimal
    block_number: int


class BlockchainWallet(Protocol):
    network: str
    asset: str

    async def latest_block_number(self) -> int: ...

    async def transfers_to_address(
        self,
        *,
        address: str,
        from_block: int,
        to_block: int,
    ) -> list[TokenTransfer]: ...

    async def transaction_confirmations(self, tx_hash: str) -> int: ...

    async def send_token(self, *, to_address: str, amount: Decimal) -> str: ...
