import asyncio

from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.smvaria import generate_preset
from ..util import checks


class SuperMetroidVaria(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def smvaria(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException('Try providing a valid subcommand.  Use "$help smvaria" for assistance.')

    @smvaria.command()
    async def race(self, ctx, skills="regular", settings="default"):
        seed = await generate_preset(
            settings=settings,
            skills=skills,
            race=True
        )
        await ctx.send(embed=seed.embed())

    @smvaria.command()
    async def norace(self, ctx, skills="regular", settings="default"):
        seed = await generate_preset(
            settings=settings,
            skills=skills,
            race=False
        )
        await ctx.send(embed=seed.embed())

def setup(bot):
    bot.add_cog(SuperMetroidVaria(bot))
