from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards.main import main_menu_keyboard
from app.database.repositories.user_repository import UserRepository
from app.database.session import transaction
from app.services.user_service import UserService

router = Router(name="start")


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return
    payload = (message.text or "").split(maxsplit=1)
    referral_code = payload[1].strip() if len(payload) == 2 else None
    async with transaction() as session:
        referred_by_id = None
        if referral_code:
            referrer = await UserRepository(session).get_by_referral_code(referral_code)
            if referrer is not None and referrer.telegram_user_id != telegram_user.id:
                referred_by_id = referrer.id
        user, wallet, created = await UserService(session).register_telegram_user(
            telegram_user_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=telegram_user.language_code,
            referred_by_id=referred_by_id,
        )
    greeting = "Welcome! Your account has been created." if created else "Welcome back."
    await message.answer(
        f"{greeting}\n\nWallet status: {wallet.status.value}\nReferral code: {user.referral_code}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def command_help(message: Message) -> None:
    await message.answer(
        "Use the inline menu to view your wallet, investment plans, investments, and referrals. "
        "Support requests should include the relevant transaction hash or request reference."
    )
