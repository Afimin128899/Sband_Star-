import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from flyerapi import Flyer

load_dotenv()

BOT_TOKEN = os.getenv("8500994183:AAFuJAtatem_2olCueCceAPi9QxMOL08_EE")
FLYER_API_KEY = os.getenv("FL-eliuMo-kzwWnO-uvimwU-UOfqjW")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

flyer = Flyer(FLYER_API_KEY)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Для использования бота нужно выполнить задания / подписаться."
    )


@dp.message()
async def check_flyer(message: types.Message):
    ok = await flyer.check(
        user_id=message.from_user.id,
        language_code=message.from_user.language_code,
    )

    if not ok:
        return  # Flyer сам отправит сообщение

    await message.answer("✅ Проверка пройдена, доступ разрешён")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

