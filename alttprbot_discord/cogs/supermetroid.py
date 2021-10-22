from discord.ext import commands

from alttprbot.alttprgen.randomizer import smdash
from alttprbot.alttprgen.smvaria import generate_league_playoff, generate_preset
from alttprbot.exceptions import SahasrahBotException


class SuperMetroid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot \
 \
                   @ commands.command()

    async def smdash(self, ctx, mode):
        url = await smdash.create_smdash(mode=mode)
        await ctx.reply(url)

    @commands.group()
    async def smvaria(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException(
                'Try providing a valid subcommand.  Use "$help smvaria" for assistance.')

    @smvaria.command()
    async def race(self, ctx, skills="regular", settings="default"):
        seed = await generate_preset(
            settings=settings,
            skills=skills,
            race=True
        )
        await ctx.reply(embed=seed.embed())

    @smvaria.command()
    async def norace(self, ctx, skills="regular", settings="default"):
        seed = await generate_preset(
            settings=settings,
            skills=skills,
            race=False
        )
        await ctx.reply(embed=seed.embed())

    @smvaria.command()
    async def playoff(self, ctx, majors, area, bosses):
        seed = await generate_league_playoff(
            majors=majors,
            area=area,
            bosses=bosses
        )
        await ctx.reply(embed=seed.embed())


def setup(bot):
    bot.add_cog(SuperMetroid(bot))
