from __future__ import annotations

import uuid

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.database.base import Base, TimestampMixin


class BlockchainScanState(TimestampMixin, Base):
    __tablename__ = "blockchain_scan_states"
    __table_args__ = (
        UniqueConstraint(
            "network", "asset", "deposit_address", name="uq_blockchain_scan_scope"
        ),
        Index(
            "ix_blockchain_scan_states_next_block",
            "network",
            "asset",
            "last_scanned_block",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    asset: Mapped[str] = mapped_column(String(16), nullable=False)
    deposit_address: Mapped[str] = mapped_column(String(128), nullable=False)
    last_scanned_block: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
