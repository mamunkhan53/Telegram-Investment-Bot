from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.models.enums import UserStatus
from app.database.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        statement = select(User).where(User.referral_code == referral_code)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(
        self, telegram_user_id: int, *, for_update: bool = False
    ) -> User | None:
        statement = select(User).where(User.telegram_user_id == telegram_user_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def register_or_update(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        referred_by_id=None,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_user_id, for_update=True)
        created = user is None
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code or "en",
                referred_by_id=referred_by_id,
            )
            self.session.add(user)
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            if language_code:
                user.language_code = language_code
            user.last_login_at = datetime.now(timezone.utc)
            if user.status != UserStatus.ACTIVE:
                raise ValueError("User account is not active.")
        await self.session.flush()
        return user, created
