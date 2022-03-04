import asyncio
import random
from datetime import datetime, timedelta
from time import sleep

import discord
from discord.ext import commands, tasks
from web3 import Web3

from joeBot import JoePic, JoeSubGraph, Constants, Utils
from joeBot.MoneyMakerBot import MoneyMaker
from joeBot.Utils import readable, Ticker

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(
    address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI
)

MIN_USD_VALUE = 5_000
SLIPPAGE = 100
time_window = 3 * 3_600
ranToday = True
started = False


class MoneyMakerTicker(commands.Cog, Ticker):
    def __init__(self, channels, callConvert):
        self.time_to_wait = 0
        self.channels = channels
        self.callConvert = callConvert

    @tasks.loop(hours=24)
    async def ticker(self):
        await asyncio.sleep(self.time_to_wait)
        try:
            await self.callConvert()

            self.time_to_wait = random.randint(0, time_window)
            await self.channels.get_channel(self.channels.BOT_ERRORS).send(
                "Info: schedule of next buyback : [{}] .".format(
                    (
                        self.ticker.next_iteration
                        + timedelta(seconds=self.time_to_wait)
                    ).strftime("%d/%m/%Y %H:%M:%S")
                )
            )

        except Exception as e:
            await self.channels.get_channel(self.channels.BOT_ERRORS).send(
                "Error on ticker: {}".format(e)
            )

    @ticker.before_loop
    async def before_ticker(self):
        now = datetime.now()
        nextRedistribution = now.replace(hour=20, minute=59, second=59)
        timeBefore9PM = (nextRedistribution - now).total_seconds()

        if timeBefore9PM < 0:
            timeBefore9PM += 86_400
            nextRedistribution += timedelta(days=1)

        self.time_to_wait = random.randint(0, time_window)
        await self.channels.get_channel(self.channels.BOT_ERRORS).send(
            "Info: schedule of next buyback : [{}].".format(
                (nextRedistribution + timedelta(seconds=self.time_to_wait)).strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )
        )

        await asyncio.sleep(timeBefore9PM)


class JoeTicker(commands.Cog, Ticker):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(seconds=60)
    async def ticker(self):
        try:
            price = JoeSubGraph.getJoePrice()
            activity = "JOE: ${}".format(round(price, 4))
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching, name=activity
                )
            )
        except Exception as e:
            print(e)
            pass


class JoeBot:
    moneyMaker = MoneyMaker
    joePic_ = JoePic.JoePic()
    discord_bot = commands.Bot
    channels = Constants.Channels
    taskManager = Utils.TaskManager

    def __init__(self, discord_bot):
        self.discord_bot = discord_bot
        for server in self.discord_bot.guilds:
            self.channels = Constants.Channels(server.id, discord_bot)
        self.moneyMaker = MoneyMaker()
        self.taskManager = Utils.TaskManager(
            (
                JoeTicker(self.discord_bot),
                MoneyMakerTicker(self.channels, self.callConvert),
            )
        )

    async def onReady(self):
        """starts joebot"""
        print("joeBot have logged in as {0.user}".format(self.discord_bot))
        await self.channels.get_channel(self.channels.BOT_ERRORS).send(
            self.taskManager.start()
        )

    async def about(self, ctx):
        about = JoeSubGraph.getAbout()
        await ctx.send(about)
        return

    async def setMinUsdValueToConvert(self, ctx):
        global MIN_USD_VALUE
        value = ctx.message.content.replace(Constants.SET_MIN_USD_COMMAND, "").strip()
        try:
            MIN_USD_VALUE = int(value)
            await ctx.send(
                "Min usd value is now set to : ${}".format(readable(MIN_USD_VALUE, 2))
            )
        except:
            await ctx.send(
                "Min usd value is currently : ${}".format(readable(MIN_USD_VALUE, 2))
            )
        return

    async def setSlippageToConvert(self, ctx):
        global SLIPPAGE
        value = ctx.message.content.replace(Constants.SET_SLIPPAGE, "").strip()
        try:
            SLIPPAGE = int(value)
            await ctx.send(
                "Slippage is now set to : {}%".format(readable(SLIPPAGE / 100, 2))
            )
        except:
            await ctx.send(
                "Slippage is currently : {}%".format(readable(SLIPPAGE / 100, 2))
            )
        return

    async def callConvert(self):
        global MIN_USD_VALUE, SLIPPAGE
        try:
            previous_avax_balance = JoeSubGraph.getAvaxBalance(
                Constants.MONEYMAKER_CALLER_ADDRESS
            )
            tx_hashs, error_on_pairs = self.moneyMaker.callConvertMultiple(
                min_usd_value=MIN_USD_VALUE, slippage=SLIPPAGE
            )
            avax_balance = JoeSubGraph.getAvaxBalance(
                Constants.MONEYMAKER_CALLER_ADDRESS
            )

            sleep(10)  # wait 10s to be sure block is confirmed
            list_of_strings = self.moneyMaker.getDailyInfo()

            if list_of_strings:
                await self.sendMessage(list_of_strings, self.channels.BOT_FEED)

            await self.channels.get_channel(self.channels.BOT_ERRORS).send(
                "Convert() tx_hashs: "
                + " ".join(tx_hashs)
                + "\nAvax Balance: {} (used {})".format(
                    readable(avax_balance, 2),
                    readable(previous_avax_balance - avax_balance, 2),
                )
            )

            if error_on_pairs:
                await self.sendMessage(error_on_pairs, self.channels.BOT_ERRORS)
        except Exception as e:
            await self.sendMessage(e.args, self.channels.BOT_ERRORS)

    async def joePic(self, ctx):
        """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile
        picture"""
        if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
            try:
                answer = self.joePic_.do_profile_picture(
                    ctx.message.content.replace(Constants.PROFILE_PICTURE_COMMAND, "")[
                        1:
                    ]
                )
                await ctx.reply(answer[0], file=answer[1])
            except ValueError:
                e = discord.Embed(
                    title="Error on {} command !".format(
                        Constants.PROFILE_PICTURE_COMMAND[1:]
                    ),
                    description=Constants.ERROR_ON_PROFILE_PICTURE,
                    color=0xF24E4D,
                )
                await ctx.reply(embed=e)
        return

    async def onCommandError(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
                e = discord.Embed(
                    title="Error on {} command !".format(
                        Constants.PROFILE_PICTURE_COMMAND[1:]
                    ),
                    description=Constants.ERROR_ON_PROFILE_PICTURE,
                    color=0xF24E4D,
                )
                await ctx.reply(embed=e)
            return
        raise error

    async def sendMessage(self, list_of_strings, channel_id=None):
        if channel_id is None:
            channel_id = self.channels.BOT_ERRORS
        message, length = [], 0
        channel = self.channels.get_channel(channel_id)
        for string in list_of_strings:
            length += len(string) + 2
            if length > 1800:
                await channel.send("\n".join(message))
                message, length = [], len(string) + 2
            message.append(string)
        if message:
            await channel.send("\n".join(message))
