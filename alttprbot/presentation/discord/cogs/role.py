import csv
import io
import re

import discord
from discord.ext import commands

import config
from alttprbot.services import ReactionRoleService
from alttprbot.exceptions import SahasrahBotException
from ..util import embed_formatter


# from emoji import is_emoji

# this is a pile of shit and needs to be refactored

DEPRECATION_MESSAGE = """
⚠️ **DEPRECATION NOTICE** ⚠️

The reaction-role feature is deprecated and will be removed in a future release.

**Recommended Migration:** Use Discord's native role assignment features:
• Server Settings → Onboarding (for new member roles)
• Channel/Server role settings
• Discord's built-in role management tools

All existing reaction-role configurations will be archived before removal.
"""

class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            return
        
        emoji = str(payload.emoji)
        role_ids = await ReactionRoleService().list_reaction_role_ids(payload.channel_id, payload.message_id, emoji, payload.guild_id)

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
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            return
        
        emoji = str(payload.emoji)
        role_ids = await ReactionRoleService().list_reaction_role_ids(payload.channel_id, payload.message_id, emoji, payload.guild_id)

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
        """Manage reaction roles (DEPRECATED - see help for details)"""
        if ctx.invoked_subcommand is None:
            await ctx.reply(DEPRECATION_MESSAGE)

    @reactionrole.command(name='create', aliases=['c'])
    async def role_create(self, ctx, group_id: int, role_name: discord.Role, name, description, emoji,
                          protect_mentions: bool = True):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        await ReactionRoleService().create_role(
            guild_id=ctx.guild.id,
            reaction_group_id=group_id,
            role_id=role_name.id,
            name=name,
            emoji=emoji,
            description=description,
            protect_mentions=protect_mentions,
        )
        await refresh_bot_message(ctx, group_id)

    @reactionrole.command(name='update', aliases=['u'])
    async def role_update(self, ctx, role_id: int, name, description, protect_mentions: bool = False):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        await ReactionRoleService().update_role(ctx.guild.id, role_id, name, description, protect_mentions)
        groups = await ReactionRoleService().get_role_group(role_id, ctx.guild.id)
        await refresh_bot_message(ctx, groups[0]['id'])

    # this is a whole pile of trash...
    @reactionrole.command(name='delete', aliases=['del'])
    async def role_delete(self, ctx, role_id: int):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        groups = await ReactionRoleService().get_role_group(role_id, ctx.guild.id)
        channel = ctx.guild.get_channel(groups[0]['channel_id'])
        message = await channel.fetch_message(groups[0]['message_id'])

        await message.remove_reaction(strip_custom_emoji(groups[0]['emoji']), ctx.bot.user)

        await ReactionRoleService().delete_role(ctx.guild.id, role_id)

        await refresh_bot_message(ctx, groups[0]['id'])

    @reactionrole.command(name='list', aliases=['l'])
    async def role_list(self, ctx, group_id: int):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # List command should work even when disabled (read-only)
        roles = await ReactionRoleService().list_group_roles(group_id, ctx.guild.id)
        await ctx.reply(embed=embed_formatter.reaction_role_list(ctx, roles))

    @commands.group(aliases=['rg'])
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def reactiongroup(self, ctx):
        """Manage reaction groups (DEPRECATED - see help for details)"""
        if ctx.invoked_subcommand is None:
            await ctx.reply(DEPRECATION_MESSAGE)

    @reactiongroup.command(name='create', aliases=['c'])
    async def group_create(self, ctx, channel: discord.TextChannel, name, description=None, bot_managed: bool = True,
                           message_id: int = None):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        if bot_managed:
            message = await channel.send('temp message')
        else:
            message = await channel.fetch_message(message_id)
        await ReactionRoleService().create_group(
            guild_id=ctx.guild.id,
            channel_id=channel.id,
            message_id=message.id,
            name=name,
            description=description,
            bot_managed=bot_managed,
        )

    @reactiongroup.command(name='update', aliases=['u'])
    async def group_update(self, ctx, group_id: int, name, description):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        await ReactionRoleService().update_group(ctx.guild.id, group_id, name, description)
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='refresh', aliases=['r'])
    async def group_refresh(self, ctx, group_id: int):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        await refresh_bot_message(ctx, group_id)

    @reactiongroup.command(name='delete', aliases=['d'])
    async def group_delete(self, ctx, group_id: int):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Check if role assignment is disabled
        if not getattr(config, 'DISCORD_ROLE_ASSIGNMENT_ENABLED', True):
            await ctx.reply("⚠️ Reaction-role functionality is currently disabled.")
            return
        
        await ReactionRoleService().delete_group(ctx.guild.id, group_id)

    @reactiongroup.command(name='list', aliases=['l'])
    async def group_list(self, ctx, group_id: int = None):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # List command should work even when disabled (read-only)
        if group_id is None:
            groups = await ReactionRoleService().list_guild_groups(ctx.guild.id)
        else:
            groups = await ReactionRoleService().get_guild_group_by_id(group_id, ctx.guild.id)
        await ctx.reply(embed=await embed_formatter.reaction_group_list(ctx, groups))

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_roles=True), commands.is_owner())
    async def importroles(self, ctx, mode=None):
        await ctx.reply(DEPRECATION_MESSAGE)
        
        # Import roles functionality still works even when reaction-roles are disabled
        # This is a utility function not directly tied to reaction-role automation
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

                if not mode == "dry":
                    await member_obj.add_roles(role_obj)
        else:
            raise SahasrahBotException("You must supply a valid csv file.")


async def refresh_bot_message(ctx, group_id):
    groups = await ReactionRoleService().get_guild_group_by_id(group_id, ctx.guild.id)
    group = groups[0]

    roles = await ReactionRoleService().list_group_roles(group_id, ctx.guild.id)

    channel = ctx.guild.get_channel(group['channel_id'])
    message = await channel.fetch_message(group['message_id'])

    for item in roles:
        #        try:
        await message.add_reaction(strip_custom_emoji(item['emoji']))
    #        except discord.errors.HTTPException as err:
    #            if err.code == 10014:
    #                await ctx.reply("That emoji is unknown to this bot.  It may be a subscriber-only or an emoji from a server this bot cannot access.  Please manually add it to the role menu!\n\nPlease note that the emoji could not be displayed on the role menu.")
    #            else:
    #                raise

    if group['bot_managed']:
        embed = embed_formatter.reaction_menu(ctx, group, roles)
        await message.edit(content=None, embed=embed)


def strip_custom_emoji(emoji):
    emoji = re.sub('^<', '', emoji)
    emoji = re.sub('>$', '', emoji)
    return emoji


async def setup(bot):
    await bot.add_cog(Role(bot))
