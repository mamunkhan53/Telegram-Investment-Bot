from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Wallet", callback_data="menu:wallet")
    builder.button(text="Investment Plans", callback_data="menu:plans")
    builder.button(text="My Investments", callback_data="menu:investments")
    builder.button(text="Referrals", callback_data="menu:referrals")
    builder.button(text="Language", callback_data="menu:language")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()


def plans_keyboard(plan_ids: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan_id in plan_ids:
        builder.button(text=f"Plan {plan_id[:8]}", callback_data=f"plan:{plan_id}")
    builder.button(text="Back", callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def wallet_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Deposit details", callback_data="wallet:deposit")
    builder.button(text="Request withdrawal", callback_data="wallet:withdraw")
    builder.button(text="Transaction history", callback_data="wallet:history")
    builder.button(text="Back", callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()
