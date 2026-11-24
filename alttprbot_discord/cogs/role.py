import csv
import io
import re

import discord
from discord.ext import commands

from alttprbot.services import reaction_roles
from alttprbot.exceptions import SahasrahBotException
from ..util import embed_formatter


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji = str(payload.emoji)
        role_ids = await reaction_roles.role_ids_for_reaction(payload.guild_id, payload.channel_id, payload.message_id,
                                                              emoji)

        if len(role_ids) == 0:
            return  # we don't want to continue, as there isn't really anything more we need to do here

        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        for role_id in role_ids:
            role_obj = guild.get_role(role_id)
            if role_obj is None:
                continue
            else:
                await member.add_roles(role_obj, reason="Added by message reaction.")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        emoji = str(payload.emoji)
        role_ids = await reaction_roles.role_ids_for_reaction(payload.guild_id, payload.channel_id, payload.message_id,
                                                              emoji)

        if len(role_ids) == 0:
            return  # we don't want to continue, as there isn't really anything more we need to do here

        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        for role_id in role_ids:
            role_obj = guild.get_role(role_id)
            if role_obj is None:
                continue
            else:
                await member.remove_roles(role_obj, reason="Removed by message reaction.")

    @commands.group(aliases=['rr'])
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def reactionrole(self, ctx):
        pass

    @reactionrole.command(name='create', aliases=['c'])
    async def role_create(self, ctx, group_id: int, role_name: discord.Role, name, description, emoji,
                          protect_mentions: bool = True):
        #        if discord.utils.find(lambda e: str(e) == emoji, ctx.bot.emojis) is None and not is_emoji(emoji):
        #            raise SahasrahBotException(
        #                'Custom emoji is not available to this bot.')

        await reaction_roles.create_role(ctx.guild.id, group_id, role_name.id, name, emoji, description,
                                         protect_mentions)
        await refresh_bot_message(ctx, group_id)

    @reactionrole.command(name='update', aliases=['u'])
    async def role_update(self, ctx, role_id: int, name, description, protect_mentions: bool = False):
        await reaction_roles.update_role(ctx.guild.id, role_id, name, description, protect_mentions)
        reaction_role = await reaction_roles.require_role(role_id, ctx.guild.id)
        await refresh_bot_message(ctx, reaction_role.reaction_group.id)

    # this is a whole pile of trash...
    @reactionrole.command(name='delete', aliases=['del'])
    async def role_delete(self, ctx, role_id: int):
        reaction_role = await reaction_roles.require_role(role_id, ctx.guild.id)
        group = reaction_role.reaction_group
        channel = ctx.guild.get_channel(group.channel_id)
        message = await channel.fetch_message(group.message_id)

        await message.remove_reaction(strip_custom_emoji(reaction_role.emoji), ctx.bot.user)

        await reaction_roles.delete_role(ctx.guild.id, role_id)

        await refresh_bot_message(ctx, group.id)

    @reactionrole.command(name='list', aliases=['l'])
    async def role_list(self, ctx, group_id: int):
        roles = await reaction_roles.group_roles(group_id, ctx.guild.id)
        await ctx.reply(embed=embed_formatter.reaction_role_list(ctx, roles))

    @commands.group(aliases=['rg'])
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def reactiongroup(self, ctx):
        pass

    @reactiongroup.command(name='create', aliases=['c'])
    async def group_create(self, ctx, channel: discord.TextChannel, name, description=None, bot_managed: bool = True,
                           message_id: int = None):
        if bot_managed:
            message = await channel.send('temp message')
        else:
            message = await channel.fetch_message(message_id)
        await reaction_roles.create_group(ctx.guild.id, channel.id, message.id, name, description, bot_managed)

    @reactiongroup.command(name='update', aliases=['u'])
    async def group_update(self, ctx, group_id: int, name, description):
        await reaction_roles.update_group(ctx.guild.id, group_id, name, description)
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='refresh', aliases=['r'])
    async def group_refresh(self, ctx, group_id: int):
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='delete', aliases=['d'])
    async def group_delete(self, ctx, group_id: int):
        await reaction_roles.delete_group(ctx.guild.id, group_id)

    @reactiongroup.command(name='list', aliases=['l'])
    async def group_list(self, ctx, group_id: int = None):
        if group_id is None:
            groups = await reaction_roles.list_groups(ctx.guild.id)
        else:
            group = await reaction_roles.get_group(group_id, ctx.guild.id)
            groups = [] if group is None else [group]
        await ctx.reply(embed=await embed_formatter.reaction_group_list(ctx, groups))

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def importroles(self, ctx, mode=None):
        if ctx.message.attachments:
            content = await ctx.message.attachments[0].read()
            role_import_list = csv.DictReader(
                io.StringIO(content.decode()))
            for i in role_import_list:
                try:
                    role_obj = await commands.RoleConverter().convert(ctx, i['role'])
                except commands.BadArgument:
                    await ctx.reply(f"Failed to find role identified by {i['role']}")
                    continue

                try:
                    member_obj = await commands.MemberConverter().convert(ctx, i['member'])
                except commands.BadArgument:
                    await ctx.reply(f"Failed to find member identified by {i['member']}")
                    continue

                if mode != "dry":
                    await member_obj.add_roles(role_obj)
        else:
            raise SahasrahBotException("You must supply a valid csv file.")


async def refresh_bot_message(ctx, group_id):
    group = await reaction_roles.require_group(group_id, ctx.guild.id)

    roles = await reaction_roles.group_roles(group_id, ctx.guild.id)

    channel = ctx.guild.get_channel(group.channel_id)
    message = await channel.fetch_message(group.message_id)

    for item in roles:
        #        try:
        await message.add_reaction(strip_custom_emoji(item.emoji))
    #        except discord.errors.HTTPException as err:
    #            if err.code == 10014:
    #                await ctx.reply("That emoji is unknown to this bot.  It may be a subscriber-only or an emoji from a server this bot cannot access.  Please manually add it to the role menu!\n\nPlease note that the emoji could not be displayed on the role menu.")
    #            else:
    #                raise

    if group.bot_managed:
        embed = embed_formatter.reaction_menu(ctx, group, roles)
        await message.edit(content=None, embed=embed)


def strip_custom_emoji(emoji):
    emoji = re.sub('^<', '', emoji)
    emoji = re.sub('>$', '', emoji)
    return emoji


async def setup(bot):
    await bot.add_cog(Role(bot))
