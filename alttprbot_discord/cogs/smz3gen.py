from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.preset import get_preset
from ..util import checks


class smz3gen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def smz3gen(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException('Try providing a valid subcommand.  Use "$help smz3gen" for assistance.')

    @smz3gen.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def preset(self, ctx, preset):
        seed, preset_dict = await get_preset(preset, randomizer='smz3')
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))


def setup(bot):
    bot.add_cog(smz3gen(bot))
