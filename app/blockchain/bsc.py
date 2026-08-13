from __future__ import annotations

import asyncio
from decimal import Decimal

from web3 import Web3
from web3.contract import Contract

from app.blockchain.wallet import TokenTransfer
from app.config.settings import Settings
from app.utils.validators import validate_bsc_address, validate_transaction_hash

ERC20_TRANSFER_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]


class BSCUSDTAdapter:
    network = "BSC"
    asset = "USDT"

    def __init__(self, settings: Settings) -> None:
        if not settings.bsc_usdt_contract_address:
            raise ValueError(
                "BSC_USDT_CONTRACT_ADDRESS is required for blockchain monitoring."
            )
        self.settings = settings
        self.web3 = Web3(
            Web3.HTTPProvider(settings.bsc_rpc_url, request_kwargs={"timeout": 20})
        )
        self.contract: Contract = self.web3.eth.contract(
            address=validate_bsc_address(settings.bsc_usdt_contract_address),
            abi=ERC20_TRANSFER_ABI,
        )

    async def latest_block_number(self) -> int:
        return await asyncio.to_thread(lambda: self.web3.eth.block_number)

    async def transfers_to_address(
        self,
        *,
        address: str,
        from_block: int,
        to_block: int,
    ) -> list[TokenTransfer]:
        checksum_address = validate_bsc_address(address)

        def fetch() -> list[TokenTransfer]:
            events = self.contract.events.Transfer().get_logs(
                from_block=from_block,
                to_block=to_block,
                argument_filters={"to": checksum_address},
            )
            decimals = int(self.contract.functions.decimals().call())
            return [
                TokenTransfer(
                    network=self.network,
                    asset=self.asset,
                    tx_hash=event["transactionHash"].hex(),
                    log_index=int(event["logIndex"]),
                    from_address=Web3.to_checksum_address(event["args"]["from"]),
                    to_address=Web3.to_checksum_address(event["args"]["to"]),
                    amount=Decimal(event["args"]["value"]) / (Decimal(10) ** decimals),
                    block_number=int(event["blockNumber"]),
                )
                for event in events
            ]

        return await asyncio.to_thread(fetch)

    async def transaction_confirmations(self, tx_hash: str) -> int:
        normalized = validate_transaction_hash(tx_hash)

        def calculate() -> int:
            receipt = self.web3.eth.get_transaction_receipt(normalized)
            latest = self.web3.eth.block_number
            if receipt is None or receipt["blockNumber"] is None:
                return 0
            return max(0, latest - int(receipt["blockNumber"]) + 1)

        return await asyncio.to_thread(calculate)

    async def send_token(self, *, to_address: str, amount: Decimal) -> str:
        """Outbound transfers require a separately injected signer and are intentionally disabled here."""
        validate_bsc_address(to_address)
        if amount <= 0:
            raise ValueError("Token transfer amount must be positive.")
        raise NotImplementedError(
            "Outbound hot-wallet signing must be implemented behind an audited signer."
        )
