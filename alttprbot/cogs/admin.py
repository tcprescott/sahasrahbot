from ..database import config, permissions
from ..util import embed_formatter
import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # get/set configuration values, only the server manager should be able to set these
    @commands.group(name='config')
    @commands.has_permissions(manage_guild=True)
    async def config_func(self, ctx):
        pass

    @config_func.command(name='set')
    async def config_set(self, ctx, parameter, value):
        await config.set_parameter(ctx.guild.id, parameter, value)

    @config_func.command(name='get')
    async def config_get(self, ctx):
        result = await config.get_parameters_by_guild(ctx.guild.id)
        await ctx.send(embed=embed_formatter.config(ctx, result))

    @config_func.command(name='delete')
    async def config_delete(self, ctx, parameter):
        await config.delete_parameter(ctx.guild.id, parameter)

    # get/set configuration values, only a server manager should be able to set these
    @commands.group(name='permission')
    @commands.has_permissions(manage_guild=True)
    async def permission_func(self, ctx):
        pass

    @permission_func.command(name='set')
    async def permission_set(self, ctx, role_name, permission):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            raise Exception('role does not exist')
        await permissions.set_permission(ctx.guild.id, role.id, permission)

    @permission_func.command(name='get')
    async def permission_get(self, ctx):
        result = await permissions.get_permissions_by_guild(ctx.guild.id)
        await ctx.send(embed=embed_formatter.permissions(ctx, result))

    @permission_func.command(name='delete')
    async def permission_delete(self, ctx, role_name, permission):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        await permissions.delete_permission(ctx.guild.id, role.id, permission)



def setup(bot):
    bot.add_cog(Admin(bot))