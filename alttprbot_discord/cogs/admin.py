from discord.ext import commands

from alttprbot_discord.util import config
from ..util import embed_formatter


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if await ctx.bot.is_owner(ctx.author) and ctx.guild:
            return True

        return False

    @commands.command(
        help='Set a parameter.'
    )
    async def configset(self, ctx, parameter, value):
        await ctx.guild.config_set(parameter, value)

    @commands.command(
        help='Get guild parameters.'
    )
    async def configget(self, ctx):
        result = await ctx.guild.config_list()
        await ctx.reply(embed=embed_formatter.config(ctx, result))

    @commands.command(
        help='Delete a parameter.'
    )
    async def configdelete(self, ctx, parameter):
        await ctx.guild.config_delete(parameter)

    @commands.command(
        brief='Clear the configuration cache.',
        help='Clear the configuration cache.  Useful if database was manually updated.'
    )
    async def configcache(self, ctx):
        await config.CACHE.clear()


def setup(bot):
    bot.add_cog(Admin(bot))
