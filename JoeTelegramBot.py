import logging, json

from aiogram import Bot, Dispatcher, executor, types
from web3 import Web3
from joeBot import JoeSubGraph, Constants, JoePic

joePic_ = JoePic.JoePic()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
with open(".key", "r") as f:
    key = json.load(f)

bot = Bot(token=key["telegram"])

dp = Dispatcher(bot)

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)

@dp.message_handler(commands='price')
async def price(message: types.Message):
    '''return the current price of $Joe'''
    price = await JoeSubGraph.getJoePrice()
    await bot.send_message(message.chat.id, "JOE price is ${}".format(round(price, 4)))

@dp.message_handler(commands='about')
async def about(message: types.Message):
    '''return the current price of $Joe, the market cap and the circulating supply.'''
    price = await JoeSubGraph.getJoePrice()
    csupply = float(w3.fromWei(joetoken_contract.functions.totalSupply().call(), 'ether'))
    mktcap = price * csupply
    await bot.send_message(message.chat.id, """JOE price is ${}\nMarket Cap: ${}\nCirculating Supply: {}""".format(round(price, 4), '{:,}'.format(int(mktcap)).replace(',', ' '), '{:,}'.format(int(csupply))).replace(',', ' '))

@dp.message_handler(commands='joepic')
async def joepic(message: types.Message):
    '''return a personnalised 3D Joe, (for more help, type /joepic).'''
    try:
        answer = joePic_.do_profile_picture(message.text[8:], "Telegram")
        await bot.send_photo(chat_id=message.chat.id, photo=open(answer, 'rb'))
    except ValueError:
        await bot.send_message(message.chat.id, Constants.ERROR_ON_PROFILE_PICTURE_TG)
        return

@dp.message_handler(commands='tokenomics')
async def tokenomics(message: types.Message):
    '''return TraderJoe's tokenomics page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoe.xyz/tokenomics")

@dp.message_handler(commands='contracts')
async def contracts(message: types.Message):
    '''return TraderJoe's contracts page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoe.xyz/contracts")

@dp.message_handler(commands='docs')
async def docs(message: types.Message):
    '''return TraderJoe's docs page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoe.xyz")

@dp.message_handler(commands='discord')
async def discord(message: types.Message):
    '''return TraderJoe's discord.'''
    await bot.send_message(message.chat.id, "https://discord.com/invite/GHZceZhbZU")

@dp.message_handler(commands='twitter')
async def twitter(message: types.Message):
    '''return TraderJoe's twitter.'''
    await bot.send_message(message.chat.id, "https://twitter.com/traderjoe_xyz")

@dp.message_handler(commands='website')
async def website(message: types.Message):
    '''return TraderJoe's website.'''
    await bot.send_message(message.chat.id, "https://www.traderjoe.xyz")

@dp.message_handler(commands='help')
async def help(message: types.Message):
    '''print Constants.HELP_TG'''
    await bot.send_message(message.chat.id, Constants.HELP_TG)



if __name__ == "__main__":
    executor.start_polling(dp)