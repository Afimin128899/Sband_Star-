from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
    ])

def check_tasks_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить задания / подписку", callback_data="check_tasks")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
    ])

def referrals_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="referrals_refresh")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")]
    ])
