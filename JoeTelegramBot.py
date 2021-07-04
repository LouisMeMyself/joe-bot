import logging

from aiogram import Bot, Dispatcher, executor, types
import json
from joeBot import JoeSubGraph


logging.basicConfig(level=logging.INFO)

with open(".key", "r") as f:
    key = json.load(f)

bot = Bot(token=key["telegram"])
# Configure logging
# Initialize bot and dispatcher
dp = Dispatcher(bot)

@dp.message_handler(commands='price')
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends message in private chat or supergroup
    """
    price = await JoeSubGraph.getJoePrice()
    await bot.send_message(message.chat.id, "JOE price is ${}".format(round(price, 4)))

if __name__ == "__main__":
    executor.start_polling(dp)