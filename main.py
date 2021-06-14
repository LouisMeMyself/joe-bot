import typing

import discord
from discord.ext import commands
from joeBot import Constants
from joeBot.JoeBot import JoeBot

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
# bot = commands.Bot(command_prefix='!')

joeBot = JoeBot


@bot.event
async def on_ready():
    """starts joebot"""
    global joeBot
    joeBot = JoeBot(bot)
    await joeBot.on_ready()


@bot.command()
async def joepic(ctx):
    """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile picture"""
    await joeBot.joepic(ctx)


@bot.command()
async def suggest(ctx):
    """command for suggestions"""
    await joeBot.suggest(ctx)


#
# @bot.command()
# async def play(ctx, msg):
#     """command for suggestions"""
#     await joeBot.play(ctx, msg)


@bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def give_all(ctx, role):
    """Gives everyone in the server a given role
    Warning : It can be slow (10 members every 8 seconds) but the bot keeps working even if this command is proceeding"""
    await joeBot.give_all(ctx, role)


@bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def remove_all(ctx, role):
    """Removes a given role to everyone in the server
    Warning : It can be slow (10 members every 8 seconds) but the bot keeps working even if this command is proceeding"""
    await joeBot.remove_all(ctx, role)


@bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def save_server(ctx):
    await joeBot.save_server(ctx)


@bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def clear(ctx, number):
    await joeBot.clear(ctx, number)


@bot.command(pass_context=True)
@commands.has_role(Constants.ROLE_FOR_CMD)
async def ban(ctx, members: commands.Greedy[discord.Member],
              delete_days: typing.Optional[int] = 0, *,
              reason: str):
    await joeBot.ban(ctx, members, delete_days, reason=reason)


@bot.event
async def on_raw_reaction_add(payload):
    """Add joe role when a reaction is added on a particular message (not a message from joebot or a
    reaction of joebot) """
    await joeBot.on_raw_reaction_add(payload)


@bot.event
async def on_raw_reaction_remove(payload):
    """harder to remove than add a role, to do"""
    await joeBot.on_raw_reaction_remove(payload)


@bot.event
async def on_command_error(ctx, error):
    await joeBot.on_command_error(ctx, error)


if __name__ == '__main__':
    with open(".key", "r") as f:
        key = f.read().replace("\n", "")
    bot.run(key)
