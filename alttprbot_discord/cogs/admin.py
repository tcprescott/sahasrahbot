from discord.ext import commands

from alttprbot.database import config
from alttprbot_srl.bot import srlbot

from ..util import embed_formatter


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # get/set configuration values, only the server manager should be able to
    # set these
    @commands.group(
        name='config',
        help='A set of commands for configuring SahasrahBot for this server.'
    )
    @commands.is_owner()
    async def config_func(self, ctx):
        pass

    @config_func.command(
        name='set',
        help='Set a parameter.'
    )
    @commands.is_owner()
    async def config_set(self, ctx, parameter, value):
        await config.set_parameter(ctx.guild.id, parameter, value)

    @config_func.command(
        name='get',
        help='Get a parameter.'
    )
    @commands.is_owner()
    async def config_get(self, ctx):
        result = await config.get_parameters_by_guild(ctx.guild.id)
        await ctx.send(embed=embed_formatter.config(ctx, result))

    @config_func.command(
        name='delete',
        help='Delete a parameter.'
    )
    @commands.is_owner()
    async def config_delete(self, ctx, parameter):
        await config.delete_parameter(ctx.guild.id, parameter)

    @commands.command()
    @commands.is_owner()
    async def srlmsg(self, ctx, channel, message):
        await srlbot.message(channel, message)

    @commands.command()
    @commands.is_owner()
    async def srljoin(self, ctx, channel):
        await srlbot.join(channel)

    @commands.command()
    @commands.is_owner()
    async def srlpart(self, ctx, channel):
        await srlbot.part(channel)

    @commands.command()
    @commands.is_owner()
    async def srlnotice(self, ctx, channel, message):
        await srlbot.notice(channel, message)

def setup(bot):
    bot.add_cog(Admin(bot))
