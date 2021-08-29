import asyncio
import logging, json
import datetime

from aiogram import Bot, Dispatcher, executor, types
from web3 import Web3
from joeBot import JoeSubGraph, JoePic, Constants
from joeBot.beautify_string import readable, human_format
import time

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


# safeguard to not spam

class Timer:
    def __init__(self):
        self.last_msg_time = {}
        self.cooldown_in_s = 1

    def canMessageOnChatId(self, chat_id):
        if chat_id not in self.last_msg_time:
            self.last_msg_time[chat_id] = 0
        if self.last_msg_time[chat_id] + self.cooldown_in_s > time.time():
            return False
        else:
            self.last_msg_time[chat_id] = time.time()
            return True


timer = Timer()


#
# @dp.message_handler()
# async def test(message: types.Message):
#     print(message.text)


@dp.message_handler(commands='startticker')
async def startTicker(message: types.Message):
    '''start joeticker'''
    if not timer.canMessageOnChatId(message.chat.id):
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not member.is_chat_admin():
        await bot.send_message(message.chat.id, "You're not admin, you can't use that command.")
        return

    if message.reply_to_message is not None and message.reply_to_message.from_user.id == bot.id:
        Constants.JOE_TICKER[message.chat.id] = message.reply_to_message.message_id
        await joeTicker(message.chat.id, message.reply_to_message.message_id)
        await bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)

    elif message.chat.id not in Constants.JOE_TICKER:
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
    time_between_updates = 10

    mess = "JOE price is $X"
    while chat_id in Constants.JOE_TICKER and Constants.JOE_TICKER[chat_id] == mess_id:
        try:
            print("joeTicker is up")
            while chat_id in Constants.JOE_TICKER and Constants.JOE_TICKER[chat_id] == mess_id:
                price = await JoeSubGraph.getJoePrice()
                new_mess = "JOE price is ${} (updated at {} UTC)".format(round(price, 4),
                                                                         datetime.datetime.utcnow().strftime(
                                                                             "%H:%M:%S"))
                if new_mess != mess:
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
            avaxp = await JoeSubGraph.getAvaxPrice()
            await bot.send_message(message.chat.id, "{} : ${}".format(msg.upper(), human_format(avaxp)))
            return
        prices = await JoeSubGraph.getPriceOf(msg)
        if prices == "Unknown Token symbol":
            await bot.send_message(message.chat.id, "Unknown token symbol, use /pricelist to know which token can be "
                                                    "tracked with JoeBot")
            return
        priceInDollar, assetPerAvax = prices
        await bot.send_message(message.chat.id,
                               "${}: ${}\n{} ${}/$AVAX".format(msg.upper(), human_format(priceInDollar),
                                                               human_format(assetPerAvax), msg.upper()))
        return
    price = float(await JoeSubGraph.getJoePrice())
    avaxp = float(await JoeSubGraph.getAvaxPrice())
    await bot.send_message(message.chat.id, "$JOE: ${}\n{} $JOE/$AVAX".format(round(price, 4), round(avaxp / price, 4)))


@dp.message_handler(commands='address')
async def address(message: types.Message):
    '''return the current price of $Joe'''
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
    '''return the current price of $Joe, the market cap and the circulating supply.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    about = await JoeSubGraph.getAbout()
    await bot.send_message(message.chat.id, about)


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


@dp.message_handler(commands='pricelist')
async def pricelist(message: types.Message):
    '''return TraderJoe's tokenomics page.'''
    if not timer.canMessageOnChatId(message.chat.id):
        return
    await JoeSubGraph.reloadAssets()
    tokens = [i.upper() for i in Constants.NAME2ADDRESS.keys()]
    await bot.send_message(message.chat.id,
                           "Tokens that can get their price from TJ are :\nAVAX, " + ", ".join(tokens))


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
    '''return a cool joe car, (for more help, type /joepic).'''
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
    global ticker_infos
    await JoeSubGraph.reloadAssets()
    await bot.send_message(message.chat.id, "Assets have been reloaded")


if __name__ == "__main__":
    executor.start_polling(dp)
