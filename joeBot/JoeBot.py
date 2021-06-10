import asyncio
import json
import typing
from datetime import datetime

import discord
from discord import NotFound
from discord.ext import commands

from constants import Constants, Channels
from joeBot import JoePic


class JoeBot:
    joePic_ = JoePic.JoePic()
    bot = commands.Bot
    channels = Channels.Channels

    def __init__(self, bot):
        self.bot = bot
        self.channels = Channels.Channels(bot)
        print(self.channels.reaction_channel, self.channels.suggestion_channel, self.channels.profile_picture)

    async def on_ready(self):
        """starts joebot"""
        for msg_id in Constants.GUIDELINES_MSG_ID:
            for channel in self.channels.reaction_channel.values():
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.add_reaction(Constants.CHECK)
                except NotFound:
                    continue
        print('joeBot have logged in as {0.user}'.format(self.bot))

    async def joepic(self, ctx):
        """command for personalised profile picture, input a color (RGB or HEX) output a reply with the profile picture"""
        print(ctx.message.content)
        if ctx.message.guild.id in self.channels.profile_picture and ctx.message.channel.id == self.channels.profile_picture[ctx.message.guild.id].id:
            answer = self.joePic_.do_profile_picture(ctx.message.content)
            if len(answer) == 2:
                await ctx.reply(answer[0], file=answer[1])
            else:
                await ctx.reply(answer)
        return

    async def on_command_error(self, ctx, error):
        if ctx.message.channel.id == self.channels.profile_picture[ctx.message.guild.id].id and isinstance(error, commands.CommandNotFound):
            await ctx.reply(Constants.ERROR_ON_JOEPIC)
            return
        raise error

    async def suggest(self, ctx):
        """command for suggestions"""
        if not ctx.message.guild.id in self.channels.suggestion_channel:
            print("Channel " + Constants.JOESUGGEST_CHANNEL_NAME + " not found in " + ctx.message.guild)
            return
        msg = ctx.message.content[9:]
        if msg != "":
            e = discord.Embed(title="Suggestion",
                              url=ctx.message.jump_url,
                              description=msg,
                              color=0xF24E4D)
            await self.channels.suggestion_channel[ctx.message.guild.id].send(embed=e)
            await ctx.message.add_reaction(Constants.CHECK)
        else:
            await ctx.reply("To make a suggestion, please do `!suggest [your suggestion here]`")
        return

    async def on_raw_reaction_add(self, payload):
        """Add joe role when a reaction is added on a particular message (not a message from joebot or a
        reaction of joebot) """
        if payload.user_id == self.bot.user.id or payload.message_id == self.bot.user.id:  # check if user that reacted is not joeBot and that the message isn't from joeBot
            return
        if not (payload.guild_id in self.channels.reaction_channel and
                self.channels.reaction_channel[payload.guild_id].id == payload.channel_id):
            return
        if payload.message_id in Constants.GUIDELINES_MSG_ID and payload.emoji.name == Constants.CHECK:
            member_ = payload.member
            role = discord.utils.get(member_.guild.roles, name=Constants.ROLE_TO_VIEW)
            await member_.add_roles(role)
        return

    async def on_raw_reaction_remove(self, payload):
        """harder to remove than add a role, to do"""
        if payload.user_id == self.bot.user.id or payload.message_id == self.bot.user.id:  # check if user that reacted is not joeBot and that the message isn't from joeBot
            return
        if not (payload.guild_id in self.channels.reaction_channel and
                self.channels.reaction_channel[payload.guild_id].id == payload.channel_id):
            return
        if payload.message_id in Constants.GUIDELINES_MSG_ID and payload.emoji == Constants.emoji:
            guild = None
            for guild in self.bot.guilds:
                if guild == payload.guild_id:
                    break
            if guild is None:
                return
            member_ = guild.get_member(payload.user_id)
            role = discord.utils.get(member_.guild.roles, name=Constants.ROLE_TO_VIEW)
            await member_.remove_roles(role)
        return

    async def give_all(self, ctx, role):
        role = discord.utils.get(ctx.guild.roles, name=role)
        for member in ctx.guild.members:
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                except:
                    print(member.name, member.id)
                print(member.name)
        await ctx.reply("Role {} has been added to everyone in the server".format(role))
        return

    async def remove_all(self, ctx, role):
        role = discord.utils.get(ctx.guild.roles, name=role)
        for member in ctx.guild.members:
            if role in member.roles:
                try:
                    await member.remove_roles(role)
                except:
                    print(member.name, member.id)
                print(member.name)
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

        with open('{}.json'.format(datetime.now().strftime("%d_%m_%Y %H_%M_%S")), 'w', encoding='utf-8') as f:
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
        if (ctx.channel.name == Constants.ADMIN_CHANNEL_NAME):  # to change to an id / channel not a name
            accept_decline = await ctx.send(
                "Do you really want to ban {}".format(" ".join([member.mention for member in members])))
            await accept_decline.add_reaction(Constants.CHECK)
            await accept_decline.add_reaction(Constants.CROSS)

            def check(reaction, user):
                return user == ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await accept_decline.delete()
                await ctx.send('Timed out')
            else:
                await accept_decline.delete()
                if reaction.emoji == Constants.CHECK:
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
