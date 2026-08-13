from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Small repository abstraction for transaction-scoped ORM operations."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id, *, for_update: bool = False) -> ModelT | None:
        statement = select(self.model).where(self.model.id == entity_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self, *conditions, limit: int = 100, offset: int = 0
    ) -> Sequence[ModelT]:
        statement = select(self.model).where(*conditions).limit(limit).offset(offset)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def exists(self, *conditions) -> bool:
        statement = select(self.model.id).where(*conditions).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_by_id(self, entity_id) -> None:
        await self.session.execute(delete(self.model).where(self.model.id == entity_id))
        await self.session.flush()
