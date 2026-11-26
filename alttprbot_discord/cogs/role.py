"""``$importroles``: give roles to members listed in a CSV. Role menus are in ``role_menus.py``."""

import csv
import io

import discord
from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException


class Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


async def setup(bot):
    await bot.add_cog(Role(bot))
