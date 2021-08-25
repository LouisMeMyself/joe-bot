import asyncio
import json
import typing
from datetime import datetime
from joeBot.beautify_string import readable, human_format
import discord
from discord.ext import commands
from web3 import Web3

from joeBot import JoePic, JoeSubGraph, Constants

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)

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
        msg = await self.channels.get_channel(self.channels.GUIDELINES_CHANNEL_ID).fetch_message(self.channels.GUIDELINES_MSG_ID)
        await msg.add_reaction(Constants.EMOJI_ACCEPT_GUIDELINES)
        print('joeBot have logged in as {0.user}'.format(self.discord_bot))
        self.discord_bot.loop.create_task(self.joeTicker())

    async def joeTicker(self):
        while 1:
            try:
                print("joeTicker is up")
                while 1:
                    price = await JoeSubGraph.getJoePrice()
                    activity = "JOE: ${}".format(round(price, 4))
                    await self.discord_bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity))
                    await asyncio.sleep(60)
            except ConnectionError:
                print("Connection error, retrying in 60 seconds...")
            except AssertionError:
                print("Assertion Error, retrying in 60 seconds...")
            except KeyboardInterrupt:
                print(KeyboardInterrupt)
                break
            await asyncio.sleep(60)

    async def about(self, ctx):
        about = await JoeSubGraph.getAbout()
        await ctx.send(about)
        return

    async def joepic(self, ctx):
        """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile picture"""
        if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID:
            try:
                answer = self.joePic_.do_profile_picture(ctx.message.content.replace(Constants.PROFILE_PICTURE_COMMAND, "")[1:])
                await ctx.reply(answer[0], file=answer[1])
            except ValueError:
                e = discord.Embed(title="Error on {} command !".format(Constants.PROFILE_PICTURE_COMMAND[1:]),
                                  description=Constants.ERROR_ON_PROFILE_PICTURE,
                                  color=0xF24E4D)
                await ctx.reply(embed=e)
        return

    async def on_command_error(self, ctx, error):
        if ctx.message.channel.id == self.channels.JOEPIC_CHANNEL_ID and isinstance(error, commands.CommandNotFound):
            e = discord.Embed(title="Error on {} command !".format(Constants.PROFILE_PICTURE_COMMAND[1:]),
                              description=Constants.ERROR_ON_PROFILE_PICTURE,
                              color=0xF24E4D)
            await ctx.reply(embed=e)
            return
        raise error

    async def suggest(self, ctx):
        """command for suggestions"""
        msg = ctx.message.content[9:]
        if msg != "":
            e = discord.Embed(title="Suggestion",
                              url=ctx.message.jump_url,
                              description=msg,
                              color=0xF24E4D)
            await self.channels.get_channel(self.channels.SUGGESTION_CHANNEL_ID).send(embed=e)
            await ctx.message.add_reaction(Constants.EMOJI_CHECK)
        else:
            await ctx.reply("To make a suggestion, please do `!suggest [your suggestion here]`")
        return

    async def on_raw_reaction_add(self, payload):
        """Add the role VERIFIED_USER_ROLE from people that react to the message in GUIDELINES_MSG_ID with the emoji EMOJI_GUIDELINES"""
        if payload.user_id == self.discord_bot.user.id or payload.message_id == self.discord_bot.user.id:  # check if user that reacted is not joeBot and that the message isn't from joeBot
            return
        if payload.channel_id == self.channels.GUIDELINES_CHANNEL_ID and payload.message_id == self.channels.GUIDELINES_MSG_ID and payload.emoji.name == Constants.EMOJI_ACCEPT_GUIDELINES:
            member_ = payload.member
            role = discord.utils.get(member_.guild.roles, name=Constants.VERIFIED_USER_ROLE)
            await member_.add_roles(role)
        return

    async def on_raw_reaction_remove(self, payload):
        """Remove the role VERIFIED_USER_ROLE from people that unreact to the message in GUIDELINES_MSG_ID"""
        if payload.user_id == self.discord_bot.user.id or payload.message_id == self.discord_bot.user.id:  # check if user that reacted is not joeBot and that the message isn't from joeBot
            return
        if payload.channel_id == self.channels.GUIDELINES_CHANNEL_ID and payload.message_id == self.channels.GUIDELINES_MSG_ID and payload.emoji.name == Constants.EMOJI_ACCEPT_GUIDELINES:
            guild = None
            for guild in self.discord_bot.guilds:
                if guild == payload.guild_id:
                    break
            if guild is None:
                return
            member_ = guild.get_member(payload.user_id)
            role = discord.utils.get(member_.guild.roles, name=Constants.VERIFIED_USER_ROLE)
            await member_.remove_roles(role)
        return

    async def give_all(self, ctx, role):
        role = discord.utils.get(ctx.guild.roles, name=role)
        for member in ctx.guild.members:
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                    print(member.name)
                except:
                    print(member.name, member.id)
        await ctx.reply("Role {} has been added to everyone in the server".format(role))
        return

    async def remove_all(self, ctx, role):
        role = discord.utils.get(ctx.guild.roles, name=role)
        for member in ctx.guild.members:
            if role in member.roles:
                try:
                    await member.remove_roles(role)
                    print(member.name)
                except:
                    print(member.name, member.id)
        await ctx.reply("Role {} has been removed to everyone in the server".format(role))
        return

    async def save_server(self, ctx):
        roles = {r.name: i for i, r in enumerate(ctx.guild.roles)}

        members = {}
        for member in ctx.guild.members:
            members[member.id] = [roles[r.name] for r in member.roles]

        categories = {channel.id: {"name": channel.name, "type": channel.type[0], "channels": {}} for channel in
                      ctx.guild.channels if channel.category_id is None}
        for channel in ctx.guild.channels:
            if channel.category_id is not None:
                categories[channel.category_id]["channels"][channel.name] = channel.type[0]

        server = {"server": categories, "member": members, "roles": roles}

        with open('save{}.json'.format(datetime.now().strftime("%d_%m_%Y %H_%M_%S")), 'w', encoding='utf-8') as f:
            json.dump(server, f, ensure_ascii=False, indent=4)

        await ctx.reply("Server has been saved")
        return

    async def clear(self, ctx, number):
        number = int(number)
        await ctx.channel.purge(limit=number)
        await ctx.send("deleted {} messages".format(number))

    async def ban(self, ctx, members: commands.Greedy[discord.Member],
                  delete_days: typing.Optional[int] = 0, *,
                  reason: str):
        """Mass bans members with an optional delete_days parameter, send a message before banning people to be sure it's not a mistake"""
        if ctx.channel.id == self.channels.COMMAND_CHANNEL_ID:  # to change to an id / channel not a name
            accept_decline = await ctx.send(
                "Do you really want to ban {}".format(" ".join([member.mention for member in members])))
            await accept_decline.add_reaction(Constants.EMOJI_CHECK)
            await accept_decline.add_reaction(Constants.EMOJI_CROSS)

            def check(reaction_, user_):
                return user_ == ctx.message.author and (str(reaction_.emoji) in (
                    Constants.EMOJI_CHECK, Constants.EMOJI_CROSS))

            try:
                reaction, user = await self.discord_bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await accept_decline.delete()
                await ctx.send('Timed out')
            else:
                await accept_decline.delete()
                if reaction.emoji == Constants.EMOJI_CHECK:
                    for member in members:
                        await member.ban(delete_message_days=delete_days, reason=reason)
                    if delete_days is not None:
                        await ctx.send(
                            "Banned {} for {} days for {}".format(" ".join([member.mention for member in members]),
                                                                  delete_days, reason))
                    else:
                        await ctx.send(
                            "Banned {} forever, for {}".format(" ".join([member.mention for member in members]),
                                                               delete_days, reason))
                else:
                    await ctx.send("Bans canceled")
