from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog
from app.database.repositories.base import Repository


class AuditRepository(Repository[AuditLog]):
    model = AuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
