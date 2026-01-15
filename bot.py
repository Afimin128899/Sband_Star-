import asyncio
import logging
import os
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from flyerapi import Flyer

from db import connect_db, init_db
from keyboards import (
    main_menu,
    back_menu,
    withdraw_menu,
    check_tasks_kb,
    referrals_kb
)

# -------------------------------------------------
# LOGGING
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# ENV
# -------------------------------------------------
def env(name, cast=str):
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"ENV {name} not set")
    return cast(val)

BOT_TOKEN = env("BOT_TOKEN")
FLYER_API_KEY = env("FLYER_API_KEY")
SUBGRAM_API_KEY = env("SUBGRAM_API_KEY")

# -------------------------------------------------
# INIT
# -------------------------------------------------
bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
flyer = Flyer(FLYER_API_KEY)
db_pool = None

# -------------------------------------------------
# SUBGRAM
# -------------------------------------------------
SUBGRAM_URL = "https://api.subgram.org/get-sponsors"

async def subgram_get_sponsors(user: types.User, chat_id: int):
    payload = {
        "user_id": user.id,
        "chat_id": chat_id,
        "first_name": user.first_name,
        "username": user.username,
        "language_code": user.language_code,
        "action": "subscribe",
        "get_links": 1,
        "max_sponsors": 5
    }
    headers = {"Auth": SUBGRAM_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SUBGRAM_URL,
                json=payload,
                headers=headers,
                timeout=10
            ) as resp:
                return await resp.json()
    except Exception as e:
        logging.error(f"SubGram error: {e}")
        return None


def subgram_text(sponsors: list) -> str:
    text = (
        "🔔 <b>Перед продолжением подпишитесь на каналы</b>\n\n"
        "Это обязательное условие для доступа к заданиям и заработку ⭐\n\n"
    )
    for i, s in enumerate(sponsors, 1):
        text += f"{i}. {s.get('title','Канал')}\n"
    text += "\nПосле подписки нажмите кнопку ниже 👇"
    return text


# -------------------------------------------------
# FLYER SAFE
# -------------------------------------------------
async def safe_flyer_check(user_id: int, lang: str) -> bool:
    try:
        return await flyer.check(user_id=user_id, language_code=lang)
    except Exception as e:
        logging.error(f"Flyer error: {e}")
        return True


# -------------------------------------------------
# REFERRAL REWARD + NOTIFICATION
# -------------------------------------------------
async def handle_referral_reward(user_id: int):
    row = await db_pool.fetchrow(
        """
        SELECT referrer_id, referral_reward_given
        FROM users
        WHERE user_id=$1
        """,
        user_id
    )

    if not row:
        return

    referrer_id = row["referrer_id"]

    if not referrer_id or row["referral_reward_given"]:
        return

    await db_pool.execute(
        """
        UPDATE users
        SET balance = balance + 2,
            referrals_count = referrals_count + 1
        WHERE user_id=$1
        """,
        referrer_id
    )

    await db_pool.execute(
        """
        UPDATE users
        SET referral_reward_given=TRUE
        WHERE user_id=$1
        """,
        user_id
    )

    balance = await db_pool.fetchval(
        "SELECT balance FROM users WHERE user_id=$1",
        referrer_id
    )

    try:
        await bot.send_message(
            referrer_id,
            "👥 <b>Новый реферал!</b>\n\n"
            f"🆔 Пользователь: <code>{user_id}</code>\n"
            "🎁 Награда: <b>+2 ⭐</b>\n\n"
            f"⭐ Текущий баланс: <b>{balance}</b>"
        )
    except:
        pass


# -------------------------------------------------
# /START
# -------------------------------------------------
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    referrer = None
    if len(args) > 1 and args[1].isdigit():
        if int(args[1]) != message.from_user.id:
            referrer = int(args[1])

    await db_pool.execute(
        """
        INSERT INTO users (user_id, referrer_id)
        VALUES ($1,$2)
        ON CONFLICT (user_id) DO NOTHING
        """,
        message.from_user.id,
        referrer
    )

    # 1️⃣ SubGram
    sg = await subgram_get_sponsors(message.from_user, message.chat.id)
    if sg and sg.get("status") == "warning":
        sponsors = sg.get("result", {}).get("sponsors", [])

        kb = []
        for s in sponsors:
            kb.append(
                [InlineKeyboardButton(text=s["title"], url=s["link"])]
            )
        kb.append(
            [InlineKeyboardButton(
                text="🔄 Проверить задания / подписку",
                callback_data="check_tasks"
            )]
        )

        await message.answer(
            subgram_text(sponsors),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return

    # 2️⃣ Flyer
    ok = await safe_flyer_check(
        message.from_user.id,
        message.from_user.language_code
    )
    if not ok:
        return

    # 3️⃣ Реферальная награда
    await handle_referral_reward(message.from_user.id)

    # 4️⃣ Меню
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Здесь ты можешь зарабатывать ⭐:\n"
        "• выполняя задания\n"
        "• подписываясь на каналы\n"
        "• приглашая друзей\n\n"
        "👇 Выбери раздел:",
        reply_markup=main_menu()
    )


# -------------------------------------------------
# CHECK TASKS / SUBSCRIPTION
# -------------------------------------------------
@dp.callback_query(lambda c: c.data == "check_tasks")
async def check_tasks(cb: CallbackQuery):
    await cb.answer("Проверяем…")

    sg = await subgram_get_sponsors(cb.from_user, cb.message.chat.id)
    if sg and sg.get("status") == "warning":
        sponsors = sg.get("result", {}).get("sponsors", [])

        kb = []
        for s in sponsors:
            kb.append(
                [InlineKeyboardButton(text=s["title"], url=s["link"])]
            )
        kb.append(
            [InlineKeyboardButton(
                text="🔄 Проверить ещё раз",
                callback_data="check_tasks"
            )]
        )

        await cb.message.edit_text(
            subgram_text(sponsors),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return

    ok = await safe_flyer_check(
        cb.from_user.id,
        cb.from_user.language_code
    )
    if not ok:
        return

    await handle_referral_reward(cb.from_user.id)

    await cb.message.edit_text(
        "✅ <b>Все обязательные условия выполнены!</b>\n\n"
        "Теперь тебе доступны задания и заработок ⭐",
        reply_markup=main_menu()
    )


# -------------------------------------------------
# TASKS
# -------------------------------------------------
@dp.callback_query(lambda c: c.data == "tasks")
async def tasks(cb: CallbackQuery):
    text = "📌 <b>Задания</b>\n\n"
    kb = []

    sg = await subgram_get_sponsors(cb.from_user, cb.message.chat.id)
    if sg and sg.get("status") == "warning":
        sponsors = sg.get("result", {}).get("sponsors", [])
        text += "🔔 <b>Обязательные подписки</b>\n\n"
        for s in sponsors:
            kb.append(
                [InlineKeyboardButton(text=s["title"], url=s["link"])]
            )
        text += "\n"

    flyer_tasks = await flyer.get_tasks(
        cb.from_user.id,
        cb.from_user.language_code,
        limit=5
    )

    if flyer_tasks:
        text += "🎯 <b>Дополнительные задания</b>\n"
        for t in flyer_tasks:
            text += f"• {t.get('name','Задание')}\n"
    else:
        text += "📭 Дополнительных заданий сейчас нет\n"

    kb.append(
        [InlineKeyboardButton(
            text="🔄 Проверить задания / подписку",
            callback_data="check_tasks"
        )]
    )
    kb.append([InlineKeyboardButton(text="🔙 В меню", callback_data="menu")])

    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


# -------------------------------------------------
# REFERRALS
# -------------------------------------------------
def referral_text(user_id: int, username: str, balance, refs: int) -> str:
    link = f"https://t.me/{username}?start={user_id}"
    return (
        "👥 <b>Реферальная система</b>\n\n"
        f"👤 Приглашено: <b>{refs}</b>\n"
        f"⭐ Баланс: <b>{balance}</b>\n\n"
        "🎁 <b>Награда:</b> +2 ⭐ за каждого реферала\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n{link}"
    )


@dp.callback_query(lambda c: c.data == "referrals")
async def referrals(cb: CallbackQuery):
    row = await db_pool.fetchrow(
        "SELECT balance, referrals_count FROM users WHERE user_id=$1",
        cb.from_user.id
    )

    await cb.message.edit_text(
        referral_text(
            cb.from_user.id,
            (await bot.get_me()).username,
            row["balance"],
            row["referrals_count"]
        ),
        reply_markup=referrals_kb()
    )


@dp.callback_query(lambda c: c.data == "referrals_refresh")
async def referrals_refresh(cb: CallbackQuery):
    row = await db_pool.fetchrow(
        "SELECT balance, referrals_count FROM users WHERE user_id=$1",
        cb.from_user.id
    )

    await cb.message.edit_text(
        referral_text(
            cb.from_user.id,
            (await bot.get_me()).username,
            row["balance"],
            row["referrals_count"]
        ),
        reply_markup=referrals_kb()
    )


# -------------------------------------------------
# MENU
# -------------------------------------------------
@dp.callback_query(lambda c: c.data == "menu")
async def menu(cb: CallbackQuery):
    await cb.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "👇 Выбери раздел:",
        reply_markup=main_menu()
    )


# -------------------------------------------------
# MAIN
# -------------------------------------------------
async def main():
    global db_pool
    db_pool = await connect_db()
    await init_db(db_pool)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
