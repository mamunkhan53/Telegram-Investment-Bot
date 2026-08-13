from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog
from app.database.repositories.audit_repository import AuditRepository
from app.utils.logger import _redact


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.logs = AuditRepository(session)

    async def record(
        self,
        *,
        action: str,
        actor_user_id=None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=_redact(payload or {}),
        )
        return await self.logs.add(log)
