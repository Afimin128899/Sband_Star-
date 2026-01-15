from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw")],
        [InlineKeyboardButton(text="🏆 ТОП рефералов", callback_data="top_refs")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
    ])

def withdraw_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 15", callback_data="wd_15"),
            InlineKeyboardButton(text="⭐ 25", callback_data="wd_25")
        ],
        [
            InlineKeyboardButton(text="⭐ 50", callback_data="wd_50"),
            InlineKeyboardButton(text="⭐ 100", callback_data="wd_100")
        ],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
    ])
