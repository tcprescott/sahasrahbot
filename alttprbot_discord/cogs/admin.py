import aiocache
from discord.ext import commands

from alttprbot.database import config
from alttprbot_srl.bot import srlbot

from ..util import embed_formatter


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True

        return False

    @commands.command(
        name='configset',
        help='Set a parameter.'
    )
    async def configset(self, ctx, parameter, value):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.set_parameter(guildid, parameter, value)

    @commands.command(
        name='configget',
        help='Get a parameter.'
    )
    async def configget(self, ctx):
        guildid = ctx.guild.id if ctx.guild else 0
        result = await config.get_parameters_by_guild(guildid)
        await ctx.send(embed=embed_formatter.config(ctx, result))

    @commands.command(
        name='configdelete',
        help='Delete a parameter.'
    )
    async def configdelete(self, ctx, parameter):
        guildid = ctx.guild.id if ctx.guild else 0
        await config.delete_parameter(guildid, parameter)

    @commands.command(
        name='configcache',
        help='Clear the configuration cache.  Useful if database was manually updated.'
    )
    async def configcache(self, ctx):
        await aiocache.SimpleMemoryCache().clear(namespace="config")

    @commands.command()
    async def srlmsg(self, ctx, channel, message):
        await srlbot.message(channel, message)

    @commands.command()
    async def srljoin(self, ctx, channel):
        await srlbot.join(channel)

    @commands.command()
    async def srlpart(self, ctx, channel):
        await srlbot.part(channel)

    @commands.command()
    async def srlnotice(self, ctx, channel, message):
        await srlbot.notice(channel, message)

    @commands.command()
    async def srljoinall(self, ctx):
        await srlbot.join_active_races(['alttphacks','alttpsm'])

def setup(bot):
    bot.add_cog(Admin(bot))
