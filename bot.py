import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from flyerapi import Flyer

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FLYER_API_KEY = os.environ.get("FLYER_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
flyer = Flyer(FLYER_API_KEY)


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет! Для доступа нужно выполнить задания / подписаться."
    )


@dp.message()
async def check(message: types.Message):
    ok = await flyer.check(
        user_id=message.from_user.id,
        language_code=message.from_user.language_code,
    )

    if not ok:
        return

    await message.answer("✅ Доступ разрешён")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

