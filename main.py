import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from joeBot import Constants, JoeMakerBot
from joeBot.JoeBot import JoeBot

# Env
load_dotenv()

# Discord
intents = discord.Intents.all()
intents.members = True

discord_bot = commands.Bot(command_prefix="!", intents=intents)

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
    """Set the min USD value."""
    await joeBot.setMinUsdValueToConvert(ctx)


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def start(ctx):
    """Start a task."""
    await ctx.reply(
        joeBot.taskManager.startTask(ctx.message.content[6:].rstrip().lstrip())
    )


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def stop(ctx):
    """Stop a task."""
    await ctx.reply(
        joeBot.taskManager.stopTask(ctx.message.content[5:].rstrip().lstrip())
    )


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def stopped(ctx):
    """Return stopped tasks."""
    await ctx.reply(joeBot.taskManager.getStoppedTasks())


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def running(ctx):
    """Return the running tasks."""
    await ctx.reply(joeBot.taskManager.getRunningTasks())


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def alltasks(ctx):
    """Return all tasks name."""
    await ctx.reply(joeBot.taskManager.getAllTasks())


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def changeversion(ctx):
    """Change JoeMaker version used to convert."""
    await ctx.reply(
        joeBot.joeMaker.changeToVersion(ctx.message.content[15:].rstrip().lstrip())
    )


# # JoeBot's wallet would need to be owner of the contract, so for now this can't be used
# @discord_bot.command(pass_context=True)
# @commands.has_role(Constants.ROLE_FOR_CMD)
# async def setbridges(ctx):
#     """SetBridges."""
#     tokens, bridges = [], []
#     for line in ctx.message.content[12:].split("\n"):
#         token, bridge = line.split(" - ")
#         tokens.append(token)
#         bridges.append(bridge)
#     await joeBot.sendMessage(
#         joeBot.joeMaker.setBridges(tokens, bridges)
#     )


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def decodetx(ctx):
    """SetBridges."""
    tx_hash = ctx.message.content[10:].lstrip().rstrip()
    await joeBot.sendMessage(JoeMakerBot.joeMaker.decodeTxHash(tx_hash))


@discord_bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def convert(ctx):
    """Calls convert on JoeMaker."""
    await joeBot.callConvert()


@discord_bot.event
async def on_command_error(ctx, error):
    await joeBot.onCommandError(ctx, error)


if __name__ == "__main__":
    # Discord
    discord_bot.run(os.getenv("DISCORD_JOEBOT_KEY"))
