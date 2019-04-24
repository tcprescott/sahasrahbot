from ..database import config, permissions
import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await ctx.message.add_reaction('⌚')

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await ctx.message.add_reaction('👍')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🚫')
            return
        if isinstance(error, commands.errors.MissingPermissions):
            await ctx.message.add_reaction('🚫')
            return
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(error)
            await ctx.message.add_reaction('👎')
        else:
            await ctx.send(error)
            await ctx.message.add_reaction('👎')
        await ctx.message.remove_reaction('⌚',ctx.bot.user)


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
        await ctx.send(embed=format_get_config(ctx, result))

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
        await ctx.send(embed=format_get_permissions(ctx, result))

    @permission_func.command(name='delete')
    async def permission_delete(self, ctx, role_name, permission):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        await permissions.delete_permission(ctx.guild.id, role.id, permission)

def format_get_permissions(ctx, permissions):
    embed = discord.Embed(title="Server Permissions", description="List of permissions and assigned roles for those permissions.", color=discord.Colour.green())
    permdict = {}
    for permission in permissions:
        role = discord.utils.get(ctx.guild.roles, id=permission['role_id']).name
        permdict.setdefault(permission['permission'], []).append(role)
    for perm in permdict:
        embed.add_field(name=perm, value='\n'.join(permdict.get(perm)), inline=False)
    return embed

def format_get_config(ctx, configdict):
    embed = discord.Embed(title="Server Configuration", description="List of configuration parameters for this server.", color=discord.Colour.teal())
    for item in configdict:
        embed.add_field(name=item['parameter'], value=item['value'])
    return embed

def setup(bot):
    bot.add_cog(Admin(bot))