import asyncio
import random
import discord

from discord.ext import commands
from web3 import Web3

from datetime import datetime, timedelta
from joeBot import JoePic, JoeSubGraph, Constants, FeeCollector
from joeBot.beautify_string import readable

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI)


class JoeBot:
    joePic_ = JoePic.JoePic()
    discord_bot = commands.Bot
    channels = Constants.Channels

    def __init__(self, discord_bot):
        self.discord_bot = discord_bot
        for server in self.discord_bot.guilds:
            self.channels = Constants.Channels(server.id, discord_bot)

    async def on_ready(self):
        """starts joebot"""
        print('joeBot have logged in as {0.user}'.format(self.discord_bot))
        self.discord_bot.loop.create_task(self.joeTicker())
        self.discord_bot.loop.create_task(self.joeMakerTicker(10000))

    async def joeMakerTicker(self, min_usd_value):
        """start JoeMakerTicker"""
        print("JoeMaker Ticker is up")
        while 1:
            while 1:
                try:
                    now = datetime.utcnow()
                    todayat8PMUTC = now.replace(hour=8, minute=0, second=0, microsecond=0)

                    if todayat8PMUTC < now:
                        nextAround8PMUTC_TS = todayat8PMUTC + timedelta(days=1, minutes=random.randint(0, 59),
                                                                        seconds=random.randint(0, 59))
                    else:
                        nextAround8PMUTC_TS = todayat8PMUTC + timedelta(days=0, minutes=random.randint(0, 59),
                                                                        seconds=random.randint(0, 59))

                    await asyncio.sleep((nextAround8PMUTC_TS - now).total_seconds())

                    previousAvaxBalance = JoeSubGraph.getAvaxBalance(Constants.JOEMAKER_CALLER_ADDRESS)
                    joeBoughtBackLast7d = JoeSubGraph.getJoeBuyBackLast7d()
                    joeBoughtBack = FeeCollector.callConvert(min_usd_value)
                    avaxBalance = JoeSubGraph.getAvaxBalance(Constants.JOEMAKER_CALLER_ADDRESS)
                    joePrice = JoeSubGraph.getJoePrice()

                    message = "\n".join(["From {} : {} $JOE".format(pair, readable(amount, 2)) for pair, amount in
                                         joeBoughtBack.items()])

                    sum_ = sum(joeBoughtBack.values())

                    message += "\nTotal buyback: {} $JOE worth ${}".format(readable(sum_, 2),
                                                                           readable(sum_ * joePrice,
                                                                                    2))
                    message += "\nLast 7 days buyback: {} $JOE worth ${}".format(
                        readable(joeBoughtBackLast7d + sum_, 2),
                        readable((joeBoughtBackLast7d + sum_) * joePrice, 2))

                    message += "\nAvax Balance: {} (used {})".format(readable(avaxBalance, 2),
                                                                     readable(previousAvaxBalance - avaxBalance, 2))

                    await self.channels.get_channel(self.channels.BOT_FEED).send(message)

                except ConnectionError:
                    print("Connection error, retrying in 60 seconds...")
                    break
                except AssertionError:
                    print("Assertion Error, retrying in 60 seconds...")
                    break
                except KeyboardInterrupt:
                    print(KeyboardInterrupt)
                    return
                except:
                    break
            print("Unknown error, retrying in 60 secs")
            await asyncio.sleep(60)

    async def joeTicker(self):
        while 1:
            print("joeTicker is up")
            try:
                while 1:
                    price = JoeSubGraph.getJoePrice()
                    activity = "JOE: ${}".format(round(price, 4))
                    await self.discord_bot.change_presence(
                        activity=discord.Activity(type=discord.ActivityType.watching, name=activity))
                    await asyncio.sleep(60)
            except ConnectionError:
                print("Connection error, retrying in 60 seconds...")
            except AssertionError:
                print("Assertion Error, retrying in 60 seconds...")
            except KeyboardInterrupt:
                print(KeyboardInterrupt)
                break
            except:
                pass
            await asyncio.sleep(60)

    async def about(self, ctx):
        about = JoeSubGraph.getAbout()
        await ctx.send(about)
        return

    async def joepic(self, ctx):
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

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
                e = discord.Embed(title="Error on {} command !".format(Constants.PROFILE_PICTURE_COMMAND[1:]),
                                  description=Constants.ERROR_ON_PROFILE_PICTURE,
                                  color=0xF24E4D)
                await ctx.reply(embed=e)
            return
        raise error
