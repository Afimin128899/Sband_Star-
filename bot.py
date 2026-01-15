import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flyerapi import Flyer
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("8500994183:AAFuJAtatem_2olCueCceAPi9QxMOL08_EE")
FLYER_KEY = os.getenv("FL-eliuMo-kzwWnO-uvimwU-UOfqjW")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

flyer = Flyer(FLYER_KEY)

# Приветствие
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply(
        "Привет! Чтобы продолжить, нужно пройти обязательную подписку / выполнить задания."
    )

# Любое сообщение — проверка Flyer
@dp.message_handler()
async def check_sub(message: types.Message):
    # Проверка подписки / выполнения задания через FlyerAPI
    ok = await flyer.check(
        message.from_user.id,
        language_code=message.from_user.language_code,
        # можно передать кастомное сообщение, если нужно
    )
    if not ok:
        # Если не подписан/задание не выполнено — фото/текст от FlyerAPI
        return

    # Если проверка прошла — обычная работа бота
    await message.reply("Вы подписались/выполнили задачу ✅")

# Команда задач (получение и проверка)
@dp.message_handler(commands=["tasks"])
async def tasks_handler(message: types.Message):
    # Получаем до 5 заданий
    tasks = await flyer.get_tasks(
        user_id=message.from_user.id,
        language_code=message.from_user.language_code,
        limit=5,
    )
    if not tasks:
        await message.reply("Нет доступных задач 🤷")
        return

    # Показываем пользователю задания
    text = "📌 Задания:\n"
    for t in tasks:
        task_name = t.get("name") or "–"
        text += f"{task_name} (sig: `{t['signature']}`)\n"
    await message.reply(text)

    # Проверяем первое задание
    sig = tasks[0]["signature"]
    status = await flyer.check_task(message.from_user.id, signature=sig)
    await message.reply(f"Статус первой задачи: {status}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
