import json

import aiohttp
import discord
import pyz3r
from discord.ext import commands

from alttprbot.alttprgen.mystery import generate_random_game
from alttprbot.alttprgen.preset import get_preset
from alttprbot.alttprgen.spoilers import generate_spoiler_game
# from config import Config as c

from ..util import checks
from ..util.alttpr_discord import alttpr


class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief='Generate a customizer game.',
        help='Generate a customizer game using a customizer save file attached to the message.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def custom(self, ctx, tournament: bool = True):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError as err:
            raise Exception('You must attach a customizer save json file.') from err

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = pyz3r.customizer.convert2settings(
            customizer_settings, tournament=tournament)

        seed = await alttpr(customizer=True, settings=settings)

        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a race preset.',
        help='Generate a race preset.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def preset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="off")
        if not seed:
            raise Exception(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a preset without the race flag enabled.',
        help='Generate a preset without the race flag enabled.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def nonracepreset(self, ctx, preset, hints=False):
        seed = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        if not seed:
            raise Exception(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        brief='Generate a spoiler game.',
        help='Generate a spoiler game.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        seed, preset_dict, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise Exception(
                'Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(f'Spoiler log <{spoiler_log_url}>', embed=embed)

    @commands.command(
        brief='Generate a game with randomized settings.',
        help='Generate a game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=5, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=False)

    @commands.command(
        brief='Generate a mystery game.',
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=5, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery", festive=False)

    @commands.command(
        brief='Generate a festive game with randomized settings.',
        help='Generate a festive game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=5, per=900, type=commands.BucketType.user)
    async def festiverandom(self, ctx, weightset='weighted', tournament: bool = True):
        await randomgame(ctx=ctx, weightset=weightset, tournament=tournament, spoilers="off", festive=True)

    @commands.command(
        brief='Generate a festive mystery game.',
        help='Generate a festive mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=5, per=900, type=commands.BucketType.user)
    async def festivemystery(self, ctx, weightset='weighted'):
        await randomgame(ctx=ctx, weightset=weightset, tournament=True, spoilers="mystery", festive=True)

    @commands.command(hidden=True, aliases=['festives'])
    async def festive(self, ctx):

        embed = discord.Embed(
            title='Festive Randomizer Information',
            description='Latest details of any upcoming festive randomizers.',
            color=discord.Color.red()
        )
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/307860211333595146/654123045375442954/unknown.png')
        await ctx.send(embed=embed)


async def randomgame(ctx, weightset, tournament=True, spoilers="off", festive=False):
    if weightset == "custom" and not ctx.message.attachments:
        raise Exception(
            'You must attach a file when specifying a custom weightset.')
    if weightset == "custom" and not ctx.message.attachments[0].filename.endswith('.yaml'):
        raise Exception('File should have a .yaml extension.')
    elif not weightset == "custom" and ctx.message.attachments:
        raise Exception(
            'If you\'re intending to use a custom weightset, please specify the weightset as "custom".')

    seed = await generate_random_game(
        weightset=weightset,
        tournament=tournament,
        spoilers=spoilers,
        custom_weightset_url=ctx.message.attachments[0].url if weightset == "custom" else None,
        festive=festive
    )
    embed = await seed.embed(emojis=ctx.bot.emojis, name="Mystery Game")
    await ctx.send(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
