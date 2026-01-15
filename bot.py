import asyncio
import logging
import os
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery

from flyerapi import Flyer

from db import connect_db, init_db
from keyboards import main_menu, back_menu, withdraw_menu

# -------------------- LOGGING --------------------
logging.basicConfig(level=logging.INFO)

# -------------------- ENV --------------------
def get_env(name: str, cast=str):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"ENV {name} is not set")
    return cast(value)

BOT_TOKEN = get_env("BOT_TOKEN")
FLYER_API_KEY = get_env("FLYER_API_KEY")
ADMIN_ID = get_env("ADMIN_ID", int)
WITHDRAW_CHANNEL_ID = get_env("WITHDRAW_CHANNEL_ID", int)

# -------------------- INIT --------------------
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
flyer = Flyer(FLYER_API_KEY)
db_pool = None


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# -------------------- SAFE FLYER --------------------
async def safe_flyer_check(user_id: int, lang: str):
    try:
        return await flyer.check(user_id=user_id, language_code=lang)
    except Exception as e:
        logging.error(f"Flyer error: {e}")
        return False


# -------------------- REFERRAL REWARD --------------------
async def process_referral_reward(user_id: int):
    row = await db_pool.fetchrow(
        "SELECT referrer_id, referral_reward_given FROM users WHERE user_id=$1",
        user_id
    )
    if not row or not row["referrer_id"] or row["referral_reward_given"]:
        return

    referrer = row["referrer_id"]

    await db_pool.execute(
        """
        UPDATE users
        SET balance = balance + 2,
            referrals_count = referrals_count + 1
        WHERE user_id=$1
        """,
        referrer
    )

    await db_pool.execute(
        "UPDATE users SET referral_reward_given=TRUE WHERE user_id=$1",
        user_id
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"⭐ Реферальная награда\nРеферал: {user_id}\nПригласил: {referrer}\n+2 ⭐"
        )
    except:
        pass


# -------------------- WEEKLY RESET --------------------
async def weekly_top_reset():
    today = date.today()
    row = await db_pool.fetchrow("SELECT last_reset FROM weekly_reset WHERE id=1")

    if row and row["last_reset"] and today - row["last_reset"] < timedelta(days=7):
        return

    await db_pool.execute("UPDATE users SET referrals_count = 0")

    await db_pool.execute(
        """
        INSERT INTO weekly_reset (id, last_reset)
        VALUES (1,$1)
        ON CONFLICT (id) DO UPDATE SET last_reset=$1
        """,
        today
    )


async def get_user_rank(user_id: int):
    row = await db_pool.fetchrow(
        """
        SELECT COUNT(*) + 1 AS rank
        FROM users
        WHERE referrals_count >
            (SELECT referrals_count FROM users WHERE user_id=$1)
        """,
        user_id
    )
    return row["rank"] if row else None


# -------------------- /start --------------------
@dp.message(CommandStart())
async def start(message: types.Message):
    args = message.text.split()
    referrer_id = None

    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == message.from_user.id:
            referrer_id = None

    await db_pool.execute(
        """
        INSERT INTO users (user_id, referrer_id)
        VALUES ($1,$2)
        ON CONFLICT (user_id) DO NOTHING
        """,
        message.from_user.id,
        referrer_id
    )

    ok = await safe_flyer_check(
        message.from_user.id,
        message.from_user.language_code
    )
    if not ok:
        return

    await process_referral_reward(message.from_user.id)

    await message.answer("👋 Добро пожаловать!", reply_markup=main_menu())


# -------------------- MENU --------------------
@dp.callback_query(lambda c: c.data == "menu")
async def menu(cb: CallbackQuery):
    await cb.message.edit_text("🏠 Главное меню", reply_markup=main_menu())


# -------------------- PROFILE --------------------
@dp.callback_query(lambda c: c.data == "profile")
async def profile(cb: CallbackQuery):
    row = await db_pool.fetchrow(
        "SELECT balance, referrals_count FROM users WHERE user_id=$1",
        cb.from_user.id
    )

    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={cb.from_user.id}"

    await cb.message.edit_text(
        f"👤 Профиль\n\n"
        f"🆔 ID: {cb.from_user.id}\n"
        f"⭐ Баланс: {row['balance']}\n"
        f"👥 Рефералов: {row['referrals_count']}\n\n"
        f"🔗 {ref_link}",
        reply_markup=back_menu()
    )


# -------------------- TASKS --------------------
@dp.callback_query(lambda c: c.data == "tasks")
async def tasks(cb: CallbackQuery):
    try:
        tasks = await flyer.get_tasks(
            cb.from_user.id,
            cb.from_user.language_code,
            limit=5
        )
    except Exception as e:
        logging.error(e)
        tasks = []

    text = "📌 Задания:\n\n"
    for t in tasks:
        text += f"• {t.get('name', 'Задание')}\n"

    await cb.message.edit_text(text, reply_markup=back_menu())


# -------------------- WITHDRAW --------------------
@dp.callback_query(lambda c: c.data == "withdraw")
async def withdraw(cb: CallbackQuery):
    await cb.message.edit_text("💸 Выберите сумму:", reply_markup=withdraw_menu())


@dp.callback_query(lambda c: c.data.startswith("wd_"))
async def withdraw_request(cb: CallbackQuery):
    try:
        amount = int(cb.data.split("_")[1])
    except:
        await cb.answer("Ошибка кнопки", show_alert=True)
        return

    row = await db_pool.fetchrow(
        "INSERT INTO withdrawals (user_id, amount) VALUES ($1,$2) RETURNING id",
        cb.from_user.id,
        amount
    )

    await cb.message.edit_text("✅ Заявка отправлена", reply_markup=back_menu())

    try:
        await bot.send_message(
            WITHDRAW_CHANNEL_ID,
            f"📤 <b>Заявка отправлена</b>\n"
            f"🆔 #{row['id']}\n👤 {cb.from_user.id}\n⭐ {amount}",
            parse_mode="HTML"
        )
    except:
        pass


# -------------------- TOP --------------------
@dp.callback_query(lambda c: c.data == "top_refs")
async def top_refs(cb: CallbackQuery):
    await weekly_top_reset()

    rows = await db_pool.fetch(
        """
        SELECT user_id, referrals_count
        FROM users
        ORDER BY referrals_count DESC
        LIMIT 10
        """
    )

    rank = await get_user_rank(cb.from_user.id)

    text = "🏆 ТОП рефералов\n\n"
    for i, r in enumerate(rows):
        text += f"{i+1}. {r['user_id']} — {r['referrals_count']}\n"

    text += f"\n📊 Ваше место: {rank}"
    await cb.message.edit_text(text, reply_markup=back_menu())


# -------------------- ADMIN --------------------
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Используй: /broadcast текст")
        return

    users = await db_pool.fetch("SELECT user_id FROM users WHERE is_banned=FALSE")

    sent = 0
    for u in users:
        try:
            await bot.send_message(u["user_id"], text)
            sent += 1
        except:
            continue

    await message.answer(f"📢 Рассылка завершена. Отправлено: {sent}")


@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("/ban USER_ID")
        return

    await db_pool.execute(
        "UPDATE users SET is_banned=TRUE WHERE user_id=$1",
        int(parts[1])
    )
    await message.answer("⛔ Пользователь забанен")


# -------------------- GLOBAL ERROR --------------------
@dp.errors()
async def global_error_handler(update, exception):
    logging.exception(f"Global error: {exception}")
    return True


# -------------------- MAIN --------------------
async def main():
    global db_pool
    while True:
        try:
            db_pool = await connect_db()
            await init_db(db_pool)
            logging.info("Bot started")
            await dp.start_polling(bot)
        except Exception as e:
            logging.exception(f"Bot crashed: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
    
