from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, Wallet
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.wallet_repository import WalletRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.wallets = WalletRepository(session)

    async def register_telegram_user(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        referred_by_id=None,
    ) -> tuple[User, Wallet, bool]:
        user, created = await self.users.register_or_update(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            referred_by_id=referred_by_id,
        )
        if created:
            user.last_login_at = datetime.now(timezone.utc)
        wallet = await self.wallets.get_or_create_for_user(user.id)
        await self.session.flush()
        return user, wallet, created
