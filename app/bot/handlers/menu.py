from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.main import main_menu_keyboard, plans_keyboard, wallet_keyboard
from app.database.session import transaction
from app.services.analytics_service import AnalyticsService

router = Router(name="menu")


def _user_id_from_callback(callback: CallbackQuery) -> int | None:
    return callback.from_user.id if callback.from_user else None


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Main menu", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:wallet")
async def menu_wallet(callback: CallbackQuery) -> None:
    telegram_id = _user_id_from_callback(callback)
    async with transaction() as session:
        analytics = AnalyticsService(session)
        user = await analytics.get_user(telegram_id) if telegram_id else None
        wallet = await analytics.get_wallet(user.id) if user else None
    if wallet is None:
        text = "Wallet not found. Use /start to register your account."
    else:
        text = (
            f"Wallet\n\nAsset: {wallet.asset}\nNetwork: {wallet.network}\n"
            f"Available: {wallet.available_balance}\nReserved: {wallet.reserved_balance}\n"
            f"Deposit address: {wallet.deposit_address or 'Pending assignment'}"
        )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=wallet_keyboard())


@router.callback_query(F.data == "menu:plans")
async def menu_plans(callback: CallbackQuery) -> None:
    async with transaction() as session:
        plans = await AnalyticsService(session).list_active_plans()
    if not plans:
        text = "No active investment plans are available at this time."
        keyboard = main_menu_keyboard()
    else:
        text = "Active investment plans:\n\n" + "\n".join(
            f"{plan.name}: {plan.minimum_amount}–{plan.maximum_amount or 'unlimited'} USDT, "
            f"{plan.duration_days} days, {plan.profit_rate}%"
            for plan in plans
        )
        keyboard = plans_keyboard([str(plan.id) for plan in plans])
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "menu:investments")
async def menu_investments(callback: CallbackQuery) -> None:
    telegram_id = _user_id_from_callback(callback)
    async with transaction() as session:
        analytics = AnalyticsService(session)
        user = await analytics.get_user(telegram_id) if telegram_id else None
        investments = await analytics.list_user_investments(user.id) if user else []
    text = "Your investments:\n\n" + (
        "\n".join(
            f"{item.id}: {item.principal_amount} USDT — {item.status.value} — profit {item.profit_amount}"
            for item in investments
        )
        if investments
        else "No investments yet."
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:referrals")
async def menu_referrals(callback: CallbackQuery) -> None:
    telegram_id = _user_id_from_callback(callback)
    async with transaction() as session:
        analytics = AnalyticsService(session)
        user = await analytics.get_user(telegram_id) if telegram_id else None
        count, rewards = await analytics.referral_summary(user.id) if user else (0, 0)
    code = user.referral_code if user else "unavailable"
    text = f"Referral code: {code}\nReferrer rewards: {count}\nTotal rewards: {rewards} USDT"
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "wallet:deposit")
async def wallet_deposit(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Send only supported USDT on BNB Smart Chain to your assigned deposit address."
    )


@router.callback_query(F.data == "wallet:history")
async def wallet_history(callback: CallbackQuery) -> None:
    telegram_id = _user_id_from_callback(callback)
    async with transaction() as session:
        analytics = AnalyticsService(session)
        user = await analytics.get_user(telegram_id) if telegram_id else None
        transactions = await analytics.transaction_history(user.id) if user else []
    text = "Transaction history:\n\n" + (
        "\n".join(
            f"{item.created_at:%Y-%m-%d} {item.transaction_type.value}: {item.amount} USDT ({item.status.value})"
            for item in transactions
        )
        if transactions
        else "No transactions yet."
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=wallet_keyboard())
