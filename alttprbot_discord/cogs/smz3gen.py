from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.smz3gen.preset import get_preset
from alttprbot.smz3gen.spoilers import generate_spoiler_game
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
        seed = await get_preset(preset)
        if not seed:
            raise SahasrahBotException('Could not generate game.  Maybe preset does not exist?')
        await ctx.send(f'Permalink: {seed.url}')


    @smz3gen.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def spoiler(self, ctx, preset):
        seed, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise SahasrahBotException('Could not generate game.  Maybe preset does not exist?')
        await ctx.send(f'Permalink: {seed.url}\nSpoiler log <{spoiler_log_url}>')


def setup(bot):
    bot.add_cog(smz3gen(bot))
