import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

from joeBot import Constants
from joeBot.JoeBot import JoeBot

# Env
load_dotenv()

# Discord
intents = discord.Intents.all()
intents.members = True

discord_bot = commands.Bot(command_prefix='!', intents=intents)

joeBot = JoeBot


@discord_bot.event
async def on_ready():
    """starts joebot"""
    global joeBot
    joeBot = JoeBot(discord_bot)
    await joeBot.onReady()


@discord_bot.command()
async def joepic(ctx):
    """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile picture"""
    await joeBot.joePic(ctx)


@discord_bot.command()
async def about(ctx):
    """return the current price of $JOE and $AVAX, the market cap, the circulating supply and the TVL."""
    await joeBot.about(ctx)


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def setmin(ctx):
    """Set the min USD valie."""
    await joeBot.setMinUsdValueToConvert(ctx)


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def convert(ctx):
    """Calls convert on JoeMakerV2."""
    await joeBot.callConvert()


@discord_bot.event
async def on_command_error(ctx, error):
    await joeBot.onCommandError(ctx, error)


if __name__ == '__main__':
    # Discord
    discord_bot.run(os.getenv("DISCORD_JOEBOT_KEY"))
