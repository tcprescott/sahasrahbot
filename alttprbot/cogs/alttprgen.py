import discord
from discord.ext import commands

from ..util.alttpr_discord import alttpr
from ..util import checks
from pyz3r.customizer import customizer

from ..alttprgen.random import generate_random_game
from ..alttprgen.preset import get_preset
from ..alttprgen.spoilers import generate_spoiler_game

from config import Config as c

import aiohttp
import json


class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        help='Generate a customizer game using a customizer save file attached to the message.'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def custom(self, ctx, tournament: bool = True):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError:
            raise Exception('You must attach a customizer save json file.')

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = customizer.convert2settings(
            customizer_settings, tournament=tournament)

        seed = await alttpr(customizer=True, settings=settings)

        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @commands.command(
        help='Generate a race preset.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def preset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="off")
        goal_name = preset_dict['goal_name']
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)


    @commands.command(
        help='Generate a preset without the tournament flag enabled.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def nonracepreset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="on", tournament=False)
        goal_name = preset_dict['goal_name']
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)


    @commands.command(
        help='Generate a spoiler game.  Find a list of presets at https://l.synack.live/presets'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    async def spoiler(self, ctx, preset):
        seed, preset_dict, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(f'Spoiler log <{spoiler_log_url}>', embed=embed)


    @commands.command(
        help='Generate a game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        if weightset == "custom" and not ctx.message.attachments:
            raise Exception('You must attach a file when specifying a custom weightset.')
        if weightset == "custom" and not ctx.message.attachments[0].filename.endswith('.yaml'):
            raise Exception('File should have a .yaml extension.')
        elif not weightset == "custom" and ctx.message.attachments:
            raise Exception('If you\'re intending to use a custom weightset, please specify the weightset as "custom".')
        
        seed = await generate_random_game(
            weightset=weightset,
            tournament=tournament,
            spoilers="off",
            custom_weightset_url=ctx.message.attachments[0].url if weightset=="custom" else None
        )
        embed = await seed.embed(emojis=self.bot.emojis, name="Random Settings Game")
        await ctx.send(embed=embed)

    @commands.command(
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @checks.restrict_to_channels_by_guild_config('AlttprGenRestrictChannels')
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted'):
        if weightset == "custom" and not ctx.message.attachments:
            raise Exception('You must attach a file when specifying a custom weightset.')
        if weightset == "custom" and not ctx.message.attachments[0].filename.endswith('.yaml'):
            raise Exception('File should have a .yaml extension.')
        elif not weightset == "custom" and ctx.message.attachments:
            raise Exception('If you\'re intending to use a custom weightset, please specify the weightset as "custom".')

        seed = await generate_random_game(
            weightset=weightset,
            tournament=True,
            spoilers="mystery",
            custom_weightset_url=ctx.message.attachments[0].url if weightset=="custom" else None
        )
        embed = await seed.embed(emojis=self.bot.emojis, name="Mystery Game")
        await ctx.send(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
