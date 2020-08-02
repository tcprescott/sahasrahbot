import asyncio

from discord.ext import commands

from alttprbot.exceptions import SahasrahBotException
from alttprbot.alttprgen.preset import get_preset
from ..util import checks


class SuperMetroidComboRandomizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def smz3(self, ctx):
        if ctx.invoked_subcommand is None:
            raise SahasrahBotException('Try providing a valid subcommand.  Use "$help smz3" for assistance.')

    @smz3.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def race(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=True)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    @smz3.command()
    @checks.restrict_to_channels_by_guild_config('Smz3GenRestrictChannels')
    async def norace(self, ctx, preset="normal"):
        seed, preset_dict = await get_preset(preset, randomizer='smz3', tournament=False)
        await ctx.send((
                f'Permalink: {seed.url}\n'
                f'Code: {seed.code}'
            ))

    # @commands.command()
    # async def smz3multi(self, ctx, preset):
    #     msg = await ctx.send("react to this message to proceed")
    #     await msg.add_reaction("✅")
    #     await msg.add_reaction('👍')

    #     def check(reaction, user):
    #         return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == msg.id

    #     try:
    #         reaction, user = await self.bot.wait_for('reaction_add', timeout=900, check=check)
    #     except asyncio.TimeoutError:
    #         await ctx.message.add_reaction('👎')
    #     else:
    #         await ctx.message.add_reaction('👍')
    #     print(reaction)
    #     print(user)
    #     print("done")

def setup(bot):
    bot.add_cog(SuperMetroidComboRandomizer(bot))
