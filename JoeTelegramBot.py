import asyncio
import datetime
import logging
import time
import os

from aiogram import Bot, Dispatcher, executor, types
from web3 import Web3

from joeBot import JoeSubGraph, JoePic, Constants, JoeChart
from joeBot.Utils import smartRounding
from dotenv import load_dotenv

# Env
load_dotenv()

joePic_ = JoePic.JoePic()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv("TELEGRAM_JOEBOT_KEY"))

dp = Dispatcher(bot)

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI)


# safeguard to not spam

class Timer:
    def __init__(self):
        self.last_msg_time = {}

    def canMessageOnChatId(self, chat_id, cd_in_s=1):
        if chat_id not in self.last_msg_time:
            self.last_msg_time[chat_id] = 0
        if self.last_msg_time[chat_id] + cd_in_s > time.time():
            return False
        else:
            self.last_msg_time[chat_id] = time.time()
            return True


timer = Timer()
time_between_updates = 60
last_reload = None


@dp.message_handler(commands='startticker')
async def startTicker(message: types.Message):
    '''start joeticker'''
    if not timer.canMessageOnChatId(message.chat.id):
        return

    # member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    # if not member.is_chat_admin():
    #     await bot.send_message(message.chat.id, "You're not admin, you can't use that command.")
    #     return

    if message.reply_to_message is not None and message.reply_to_message.from_user.id == bot.id:
        Constants.JOE_TICKER[message.chat.id] = message.reply_to_message.message_id
        await joeTicker(message.chat.id, message.reply_to_message.message_id)
        await bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)

    else:
        mess_id = (await bot.send_message(message.chat.id, "JOE price is $X")).message_id
        Constants.JOE_TICKER[message.chat.id] = mess_id
        await bot.pin_chat_message(message.chat.id, mess_id)
        await joeTicker(message.chat.id, mess_id)


@dp.message_handler(commands='stopticker')
async def stopTicker(message: types.Message):
    '''stop joeTicker'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    chat_id = message.chat.id
    member = await bot.get_chat_member(chat_id, message.from_user.id)
    if not member.is_chat_admin():
        return
    if message.chat.id in Constants.JOE_TICKER:
        await bot.send_message(chat_id, "JoeTicker stopped.")
        await bot.delete_message(chat_id, Constants.JOE_TICKER[chat_id])
        Constants.JOE_TICKER.pop(chat_id)

    elif message.reply_to_message is not None and message.reply_to_message.from_user.id == bot.id:
        mid = message.reply_to_message.message_id
        try:
            await bot.send_message(chat_id, "JoeTicker stopped.")
            await bot.delete_message(chat_id, mid)
        except:
            pass
    else:
        await bot.send_message(chat_id, "JoeTicker not started.")


async def joeTicker(chat_id, mess_id):
    global last_reload
    mess = "JOE price is $X"
    while chat_id in Constants.JOE_TICKER and Constants.JOE_TICKER[chat_id] == mess_id:
        try:
            print("joeTicker is up")
            while chat_id in Constants.JOE_TICKER and Constants.JOE_TICKER[chat_id] == mess_id:
                price = JoeSubGraph.getJoePrice()
                new_mess = "JOE price is ${} (updated at {} UTC)".format(round(price, 4),
                                                                         datetime.datetime.utcnow().strftime(
                                                                             "%H:%M:%S"))
                if last_reload is None or (datetime.datetime.utcnow() - last_reload).total_seconds() < 3600:
                    JoeSubGraph.reloadAssets()
                    last_reload = datetime.datetime.utcnow()

                if new_mess != mess:
                    JoeSubGraph.reloadAssets()
                    mess = new_mess
                    await bot.edit_message_text(mess, chat_id, mess_id)
                await asyncio.sleep(time_between_updates)
        except ConnectionError:
            print("Connection error, retrying in 60 seconds...")
        except AssertionError:
            print("Assertion Error, retrying in 60 seconds...")
        except KeyboardInterrupt:
            print(KeyboardInterrupt)
            break
        except:
            pass
        await asyncio.sleep(time_between_updates)
    return


@dp.message_handler(commands='price')
async def price(message: types.Message):
    '''return the current price of $Joe'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    msg = message.text.lower().replace("/price", "").replace(" ", "")
    if msg != "" and msg != "joe":
        if msg == "avax":
            avaxp = JoeSubGraph.getAvaxPrice()
            await bot.send_message(message.chat.id, "${} : ${}".format(msg.upper(), smartRounding(avaxp)))
            return
        prices = JoeSubGraph.getPricesOf(msg)
        if len(prices) != 2:
            await bot.send_message(message.chat.id, prices + "\nUse /pricelist to know which token can be "
                                                             "tracked with JoeBot")
            return
        derivedPrice, priceInDollar = prices
        await bot.send_message(message.chat.id,
                               "${}: ${}\n{} ${}/$AVAX".format(msg.upper(), smartRounding(priceInDollar),
                                                               smartRounding(1 / derivedPrice), msg.upper()))
        return

    prices = JoeSubGraph.getPricesOf(Constants.JOETOKEN_ADDRESS)

    if len(prices) != 2:
        await bot.send_message(message.chat.id, prices)
        return
    dprice, price = prices
    await bot.send_message(message.chat.id, "$JOE: ${}\n{} $JOE/$AVAX".format(round(price, 4), round(1 / dprice, 4)))


@dp.message_handler(commands='address')
async def address(message: types.Message):
    '''return the address of a token (not working for all the tokens)'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    msg = message.text.lower().replace("/address", "").replace(" ", "")
    if msg != "":
        if msg == "avax":
            await bot.send_message(message.chat.id, "$WAVAX: 0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")
            return
        if msg in Constants.NAME2ADDRESS:
            await bot.send_message(message.chat.id, "${}: {}".format(msg.upper(), Constants.NAME2ADDRESS[msg]))
        else:
            await bot.send_message(message.chat.id, "Unknown token symbol, use /pricelist to know which token can be "
                                                    "tracked with JoeBot")


@dp.message_handler(commands='about')
async def about(message: types.Message):
    '''return the current price of $JOE and $AVAX, the market cap, the circulating supply and the TVL.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    about = JoeSubGraph.getAbout()
    await bot.send_message(message.chat.id, about)


@dp.message_handler(commands='lending')
async def lending(message: types.Message):
    '''return the current Lending Total Supply of Banker Joe.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    lendingAbout = JoeSubGraph.getLendingAbout()
    await bot.send_message(message.chat.id, lendingAbout)


@dp.message_handler(commands='joepic')
async def joepic(message: types.Message):
    '''return a personnalised 3D Joe, (for more help, type /joepic).'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    try:
        answer = joePic_.do_profile_picture(message.text[8:], "Telegram")
        await bot.send_photo(chat_id=message.chat.id, photo=open(answer, 'rb'))
    except ValueError:
        await bot.send_message(message.chat.id, Constants.ERROR_ON_PROFILE_PICTURE_TG)
        return


@dp.message_handler(commands='avg7d')
async def avg7d(message: types.Message):
    '''return the average price on the last 42 4hours close data (7-day averaged).'''
    if not timer.canMessageOnChatId(message.chat.id):
        return

    try:
        answer = JoeSubGraph.avg7d(message.text[7:].replace(" ", ""))
        if answer == -1:
            await bot.send_message(message.chat.id, "Not enough data.")
            return
        await bot.send_message(message.chat.id, "7day average $JOE: ${}".format(smartRounding(answer)))
    except:
        await bot.send_message(message.chat.id, "An error occured, please use `/avg7d [timestamp]` to get the "
                                                "7 day average $JOE price")
    return


@dp.message_handler(commands='pricelist')
async def pricelist(message: types.Message):
    '''Returns the list of tokens for which you can request their price from joebot with !price.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    addresses = list(Constants.NAME2ADDRESS.keys())
    addresses.sort()
    tokens = [i.upper() for i in addresses]
    await bot.send_message(message.chat.id,
                           "Tokens that can get their price from TJ are :\nAVAX, " + ", ".join(tokens))


@dp.message_handler(commands='chart')
async def chart(message: types.Message):
    '''return the chart of a token (not working for all the tokens).'''
    if not timer.canMessageOnChatId(message.chat.id):
        return

    msgs = message.text[7:].split(" ")
    if msgs[-1] == "d" or msgs[-1] == "days":
        period = "day"
    else:
        period = "month"
    if msgs[0] == "":
        await JoeChart.getChart("joe", period)
    else:
        await JoeChart.getChart(msgs[0], period)
    await bot.send_photo(chat_id=message.chat.id, photo=open("content/images/chart.png", 'rb'))
    return


@dp.message_handler(commands='lambo')
async def lambo(message: types.Message):
    '''return a cool joe car.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_video(chat_id=message.chat.id, video=open("content/videos/joelambo.mp4", 'rb'),
                         supports_streaming=True)
    return


@dp.message_handler(commands='rain')
async def rain(message: types.Message):
    '''return a cool joe rain.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_video(chat_id=message.chat.id, video=open("content/videos/joerain.mp4", 'rb'),
                         supports_streaming=True)
    return


@dp.message_handler(commands='comfy')
async def comfy(message: types.Message):
    '''return a cool joe comfy.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_photo(chat_id=message.chat.id, photo=open("content/images/joecomfy.png", 'rb'))
    return


@dp.message_handler(commands='tokenomics')
async def tokenomics(message: types.Message):
    '''return TraderJoe's tokenomics page.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com/en/tokenomics")


@dp.message_handler(commands='contracts')
async def contracts(message: types.Message):
    '''return TraderJoe's contracts page.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com/en/contracts")


@dp.message_handler(commands='docs')
async def docs(message: types.Message):
    '''return TraderJoe's docs page.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://docs.traderjoexyz.com")


@dp.message_handler(commands='discord')
async def discord(message: types.Message):
    '''return TraderJoe's discord.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://discord.com/invite/GHZceZhbZU")


@dp.message_handler(commands='twitter')
async def twitter(message: types.Message):
    '''return TraderJoe's twitter.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://twitter.com/traderjoe_xyz")


@dp.message_handler(commands='website')
async def website(message: types.Message):
    '''return TraderJoe's website.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, "https://www.traderjoexyz.com")


@dp.message_handler(commands='help')
async def help(message: types.Message):
    '''print Constants.HELP_TG'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await bot.send_message(message.chat.id, Constants.HELP_TG)


@dp.message_handler(commands='reloadassets')
async def reloadAssets(message: types.Message):
    '''reload assets'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    JoeSubGraph.reloadAssets()
    await bot.send_message(message.chat.id, "Assets have been reloaded")


if __name__ == "__main__":
    executor.start_polling(dp)