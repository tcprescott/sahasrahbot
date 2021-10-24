from discord.ext import commands

from alttprbot.alttprgen import generator
from ..util import checks


class CTJets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('CTJetsGenRestrictChannels')
    async def ctjets(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.reply('Please specify a subcommand!')

    @ctjets.command(
        help='Generates a Chrono Trigger Jets of Time Race.\nThis game will not have a spoiler log.\nA list of presets can be found at <https://github.com/tcprescott/sahasrahbot/tree/master/presets/ctjets>.',
        brief='Generates a Chrono Trigger Jets of Time Race.'
    )
    @checks.restrict_to_channels_by_guild_config('CTJetsGenRestrictChannels')
    async def preset(self, ctx, preset):
        seed_uri = await generator.CTJetsPreset(preset).generate()
        await ctx.reply(seed_uri)

def setup(bot):
    bot.add_cog(CTJets(bot))
