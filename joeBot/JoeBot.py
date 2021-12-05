import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from web3 import Web3

from joeBot import JoePic, JoeSubGraph, Constants, JoeMakerBot, Utils
from joeBot.JoeMakerBot import JoeMaker
from joeBot.Utils import readable, Ticker

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI)

MIN_USD_VALUE = 10000
ranToday = True
started = False


class JoeMakerTicker(commands.Cog, Ticker):
    def __init__(self, channels, callConvert):
        self.ranToday = True
        self.channels = channels
        self.callConvert = callConvert

    @tasks.loop(hours=24)
    async def ticker(self):
        print("ticker")
        try:
            if self.ranToday:
                time_to_wait = random.randint(0, 3600)
                await asyncio.sleep(time_to_wait)
                await self.callConvert()

                self.ranToday = True

                await self.channels.get_channel(self.channels.BOT_ERRORS).send(
                    "Info: schedule of next buyback : [{}] .".format(self.ticker.next_iteration +
                                                                     timedelta(seconds=time_to_wait)))
            else:
                await self.channels.get_channel(self.channels.BOT_ERRORS).send(
                    "Error: JoeMaker didn't convert today, retrying in 60 seconds.")

        except Exception as e:
            await self.channels.get_channel(self.channels.BOT_ERRORS).send("Error: {}".format(e))
            self.ranToday = False

    @ticker.before_loop
    async def before_ticker(self):
        now = datetime.now()
        timeBefore11PM30 = (now.replace(hour=23, minute=30) - now).total_seconds()

        if timeBefore11PM30 < 0:
            timeBefore11PM30 += timedelta(days=1)

        await self.channels.get_channel(self.channels.BOT_ERRORS).send(
            "Info: schedule of next buyback : [{}] +- 30 min.".format(
                datetime.fromtimestamp(now.replace(hour=0, minute=0).timestamp()).strftime(
                                                                             "%D %H:%M")))

        await asyncio.sleep(timeBefore11PM30)


class JoeTicker(commands.Cog, Ticker):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(seconds=60)
    async def ticker(self):
        try:
            price = JoeSubGraph.getJoePrice()
            activity = "JOE: ${}".format(round(price, 4))
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=activity))
        except Exception as e:
            print(e)
            pass


class JoeBot:
    joePic_ = JoePic.JoePic()
    discord_bot = commands.Bot
    channels = Constants.Channels
    taskManager = Utils.TaskManager
    joeMaker = JoeMaker

    def __init__(self, discord_bot):
        self.discord_bot = discord_bot
        for server in self.discord_bot.guilds:
            self.channels = Constants.Channels(server.id, discord_bot)
        self.joeMaker = JoeMaker()
        self.taskManager = Utils.TaskManager(
            (
                JoeTicker(self.discord_bot),
                JoeMakerTicker(self.channels, self.callConvert)
            )
        )

    async def onReady(self):
        """starts joebot"""
        global started
        print('joeBot have logged in as {0.user}'.format(self.discord_bot))
        if not started:
            await self.channels.get_channel(self.channels.BOT_ERRORS).send(self.taskManager.start())
            started = True

    async def about(self, ctx):
        about = JoeSubGraph.getAbout()
        await ctx.send(about)
        return

    async def setMinUsdValueToConvert(self, ctx):
        global MIN_USD_VALUE
        value = ctx.message.content.replace(Constants.SET_MIN_USD_COMMAND, "").rstrip().lstrip()
        try:
            MIN_USD_VALUE = float(value)
            await ctx.send("Min usd value is now set to : ${}".format(readable(MIN_USD_VALUE, 2)))
        except:
            await ctx.send("Min usd value is currently : ${}".format(readable(MIN_USD_VALUE, 2)))
        return

    async def callConvert(self):
        previous_avax_balance = JoeSubGraph.getAvaxBalance(Constants.JOEMAKER_CALLER_ADDRESS)
        joe_bought_back_last7d = JoeSubGraph.getJoeBuyBackLast7d()
        pairs, joe_bought_back, error_on_pairs = JoeBot.joeMaker.callConvertMultiple(MIN_USD_VALUE)
        avax_balance = JoeSubGraph.getAvaxBalance(Constants.JOEMAKER_CALLER_ADDRESS)
        joe_price = JoeSubGraph.getJoePrice()

        list_of_string = ["{} : {} $JOE".format(pair, readable(amount, 2)) for pair, amount in
                          zip(pairs, joe_bought_back)]

        sum_ = sum(joe_bought_back)

        list_of_string.append("Total buyback: {} $JOE worth ${}".format(readable(sum_, 2),
                                                                        readable(sum_ * joe_price, 2)))
        list_of_string.append("Last 7 days buyback: {} $JOE worth ${}".format(
            readable(joe_bought_back_last7d + sum_, 2),
            readable((joe_bought_back_last7d + sum_) * joe_price, 2)))

        await self.sendMessage(list_of_string, self.channels.BOT_FEED)

        await self.channels.get_channel(self.channels.BOT_ERRORS).send(
            "Avax Balance: {} (used {})".format(readable(avax_balance, 2),
                                                readable(previous_avax_balance - avax_balance, 2)))

        if len(error_on_pairs) > 0:
            await self.sendMessage(error_on_pairs, self.channels.BOT_ERRORS)

    async def joePic(self, ctx):
        """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile
        picture """
        if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
            try:
                answer = self.joePic_.do_profile_picture(
                    ctx.message.content.replace(Constants.PROFILE_PICTURE_COMMAND, "")[1:])
                await ctx.reply(answer[0], file=answer[1])
            except ValueError:
                e = discord.Embed(title="Error on {} command !".format(Constants.PROFILE_PICTURE_COMMAND[1:]),
                                  description=Constants.ERROR_ON_PROFILE_PICTURE,
                                  color=0xF24E4D)
                await ctx.reply(embed=e)
        return

    async def onCommandError(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
                e = discord.Embed(title="Error on {} command !".format(Constants.PROFILE_PICTURE_COMMAND[1:]),
                                  description=Constants.ERROR_ON_PROFILE_PICTURE,
                                  color=0xF24E4D)
                await ctx.reply(embed=e)
            return
        raise error

    async def sendMessage(self, list_of_strings, channel_id):
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
