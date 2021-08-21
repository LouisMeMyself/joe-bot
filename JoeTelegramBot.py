import asyncio
import logging, json
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from web3 import Web3
from joeBot import JoeSubGraph, JoePic, Constants
from utils.beautify_string import readable, human_format

joePic_ = JoePic.JoePic()
ticker_infos = {"started": False, "chat_id": 0}

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

@dp.message_handler(commands='startticker')
async def startTicker(message: types.Message):
    global ticker_infos
    '''return the current price of $Joe'''
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not member.is_chat_admin():
        await bot.send_message(message.chat.id, "You're not admin, you can't use that command.")
        return
    if not ticker_infos["started"]:
        ticker_infos["started"] = True
        ticker_infos["chat_id"] = message.chat.id
        await joeTicker()
    else:
        await bot.send_message(message.chat.id, "JoeTicker already started.")

@dp.message_handler(commands='stopticker')
async def stoptTicker(message: types.Message):
    global ticker_infos
    '''return the current price of $Joe'''
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not member.is_chat_admin():
        return
    ticker_infos["started"] = False
    ticker_infos["chat_id"] = 0

    await bot.send_message(message.chat.id, "JoeTicker stopped.")


async def joeTicker():
    time_between_updates = 10
    mess_id = await bot.send_message(ticker_infos["chat_id"],
                           "JOE price is $X")
    mess = "JOE price is $X"
    while ticker_infos["started"]:
        try:
            print("joeTicker is up")
            while ticker_infos["started"]:
                price = await JoeSubGraph.getJoePrice()
                new_mess = "JOE price is ${} (updated at {} UTC)".format(round(price, 4), datetime.utcnow().strftime("%H:%M:%S"))
                if new_mess != mess:
                    mess = new_mess
                    await bot.edit_message_text(mess, ticker_infos["chat_id"], mess_id.message_id )
                await asyncio.sleep(time_between_updates)
        except ConnectionError:
            print("Connection error, retrying in 60 seconds...")
        except AssertionError:
            print("Assertion Error, retrying in 60 seconds...")
        except KeyboardInterrupt:
            print(KeyboardInterrupt)
            break
        await asyncio.sleep(time_between_updates)

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
    tvl = await JoeSubGraph.getTVL()
    await bot.send_message(message.chat.id, """JOE price is ${}
Market Cap: ${}
Circ. Supply: {}
TVL: ${}""".format(readable(price, 4), human_format(mktcap), human_format(csupply), human_format(tvl)))

@dp.message_handler(commands='joepic')
async def joepic(message: types.Message):
    '''return a personnalised 3D Joe, (for more help, type /joepic).'''
    try:
        answer = joePic_.do_profile_picture(message.text[8:], "Telegram")
        await bot.send_photo(chat_id=message.chat.id, photo=open(answer, 'rb'))
    except ValueError:
        await bot.send_message(message.chat.id, Constants.ERROR_ON_PROFILE_PICTURE_TG)
        return

@dp.message_handler(commands='lambo')
async def lambo(message: types.Message):
    '''return a cool joe car.'''
    await bot.send_video(chat_id=message.chat.id, video=open("utils/joelambo.mp4", 'rb'), supports_streaming=True)
    return

@dp.message_handler(commands='rain')
async def rain(message: types.Message):
    '''return a cool joe rain.'''
    await bot.send_video(chat_id=message.chat.id, video=open("utils/joerain.mp4", 'rb'), supports_streaming=True)
    return

@dp.message_handler(commands='comfy')
async def comfy(message: types.Message):
    '''return a cool joe car, (for more help, type /joepic).'''
    await bot.send_photo(chat_id=message.chat.id, photo=open("utils/joecomfy.png", 'rb'))
    return

@dp.message_handler(commands='tokenomics')
async def tokenomics(message: types.Message):
    '''return TraderJoe's tokenomics page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com/en/tokenomics")

@dp.message_handler(commands='contracts')
async def contracts(message: types.Message):
    '''return TraderJoe's contracts page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com/en/contracts")

@dp.message_handler(commands='docs')
async def docs(message: types.Message):
    '''return TraderJoe's docs page.'''
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com")

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
    await bot.send_message(message.chat.id, "https://www.traderjoexyz.com")

@dp.message_handler(commands='help')
async def help(message: types.Message):
    '''print Constants.HELP_TG'''
    await bot.send_message(message.chat.id, Constants.HELP_TG)

if __name__ == "__main__":
    executor.start_polling(dp)