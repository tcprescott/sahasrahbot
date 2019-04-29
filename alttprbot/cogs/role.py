
import discord
from discord.ext import commands
from ..database import role
from ..util import embed_formatter
import re

from emoji import UNICODE_EMOJI

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji = str(payload.emoji)
        roles = await role.get_role_by_group_emoji(payload.channel_id, payload.message_id, emoji, payload.guild_id)

        if len(roles) == 0:
            return #we don't want to continue, as there isn't really anything more we need to do here

        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        role_list = []
        for roleids in roles:
            role_obj = guild.get_role(roleids['role_id'])
            if role_obj == None:
                continue
            else:
                await member.add_roles(role_obj, reason="Added by message reaction.")
            
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        emoji = str(payload.emoji)
        roles = await role.get_role_by_group_emoji(payload.channel_id, payload.message_id, emoji, payload.guild_id)

        if len(roles) == 0:
            return #we don't want to continue, as there isn't really anything more we need to do here

        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        role_list = []
        for roleids in roles:
            role_obj = guild.get_role(roleids['role_id'])
            if role_obj == None:
                continue
            else:
                await member.remove_roles(role_obj, reason="Removed by message reaction.")


    @commands.group(aliases=['rr'])
    @commands.has_permissions(manage_roles=True)
    async def reactionrole(self, ctx):
        pass

    @reactionrole.command(name='create', aliases=['c'])
    async def role_create(self, ctx, group_id: int, role_name: discord.Role, name, description, emoji, protect_mentions: bool=True):
        existing_roles = await role.get_group_roles(group_id, ctx.guild.id)
        if len(existing_roles) >= 20:
            raise Exception('No more than 20 roles can be on a group.  Please create a new group.')

        if discord.utils.find(lambda e: str(e) == emoji, ctx.bot.emojis) == None and is_emoji(emoji) == False:
            raise Exception('Custom emoji is not available to this bot.')

        await role.create_role(ctx.guild.id, group_id, role_name.id, name, emoji, description, protect_mentions)
        await refresh_bot_message(ctx, group_id)

    @reactionrole.command(name='update', aliases=['u'])
    async def role_update(self, ctx, role_id: int, name, description, protect_mentions: bool=False):
        await role.update_role(ctx.guild.id, role_id, name, description, protect_mentions)
        groups = await role.get_role_group(role_id, ctx.guild.id)
        await refresh_bot_message(ctx, groups[0]['id'])

    # this is a whole pile of trash...
    @reactionrole.command(name='delete', aliases=['del'])
    async def role_delete(self, ctx, role_id: int):
        groups = await role.get_role_group(role_id, ctx.guild.id)
        channel = ctx.guild.get_channel(groups[0]['channel_id'])
        message = await channel.fetch_message(groups[0]['message_id'])

        await message.remove_reaction(strip_custom_emoji(groups[0]['emoji']), ctx.bot.user)

        await role.delete_role(ctx.guild.id, role_id)

        await refresh_bot_message(ctx, groups[0]['id'])

    @reactionrole.command(name='list', aliases=['l'])
    async def role_list(self, ctx, group_id: int):
        roles = await role.get_group_roles(group_id, ctx.guild.id)
        await ctx.send(embed=embed_formatter.reaction_role_list(ctx, roles))






    @commands.group(aliases=['rg'])
    @commands.has_permissions(manage_roles=True)
    async def reactiongroup(self, ctx):
        pass

    @reactiongroup.command(name='create', aliases=['c'])
    async def group_create(self, ctx, channel: discord.TextChannel, name, description=None, bot_managed: bool=True, message_id: int=None):
        if bot_managed:
            message = await channel.send('temp message')
        else:
            message = await channel.fetch_message(message_id)
        await role.create_group(ctx.guild.id, channel.id, message.id, name, description, bot_managed)

    @reactiongroup.command(name='update', aliases=['u'])
    async def group_update(self, ctx, group_id: int, name, description):
        await role.update_group(ctx.guild.id, group_id, name, description)
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='refresh', aliases=['r'])
    async def group_refresh(self, ctx, group_id: int):
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='delete', aliases=['d'])
    async def group_delete(self, ctx, group_id: int):
        await role.delete_group(ctx.guild.id, group_id)

    @reactiongroup.command(name='list', aliases=['l'])
    async def group_list(self, ctx, group_id: int=None):
        if group_id==None:
            groups = await role.get_guild_groups(ctx.guild.id)
        else:
            groups = await role.get_guild_group_by_id(group_id, ctx.guild.id)
        await ctx.send(embed=await embed_formatter.reaction_group_list(ctx, groups))
    
async def refresh_bot_message(ctx, group_id):
    groups = await role.get_guild_group_by_id(group_id, ctx.guild.id)
    group = groups[0]

    roles = await role.get_group_roles(group_id, ctx.guild.id)

    channel = ctx.guild.get_channel(group['channel_id'])
    message = await channel.fetch_message(group['message_id'])

    for item in roles:
        await message.add_reaction(strip_custom_emoji(item['emoji']))

    if group['bot_managed']:
        embed = embed_formatter.reaction_menu(ctx, group, roles)
        await message.edit(content=None, embed=embed)

def strip_custom_emoji(emoji):
    emoji = re.sub('^<','',emoji)
    emoji = re.sub('>$','',emoji)
    return emoji

def is_emoji(s):
    count = 0
    for emoji in UNICODE_EMOJI:
        count += s.count(emoji)
        if count > 1:
            return False
    return bool(count)

def setup(bot):
    bot.add_cog(Role(bot))