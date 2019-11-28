import discord
from discord.ext import commands

from ..util.alttpr_discord import alttpr
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

    @commands.command(hidden=True)
    async def seedgen(self, ctx, cmd):
        await ctx.send(f'You can just use ${cmd} from now on!')

    @commands.command(
        help='Generate a customizer game using a customizer save file attached to the message.'
    )
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
        help='Generate a preset.  Find a list of presets at https://l.synack.live/presets'
    )
    async def preset(self, ctx, preset, hints=False):
        seed, preset_dict = await get_preset(preset, hints=hints, spoilers="off")
        goal_name = preset_dict['goal_name']
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(embed=embed)


    @commands.command(
        help='Generate a spoiler game.  Find a list of presets at https://l.synack.live/presets'
    )
    async def spoiler(self, ctx, preset):
        seed, preset_dict, spoiler_log_url = await generate_spoiler_game(preset)
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await seed.embed(emojis=self.bot.emojis)
        await ctx.send(f'Spoiler log <{spoiler_log_url}>', embed=embed)


    @commands.command(
        help='Generate a game with randomized settings.  Find a list of weights at https://l.synack.live/weights'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(weightset=weightset, tournament=tournament, spoilers="off")
        embed = await seed.embed(emojis=self.bot.emojis, name="Random Race Game")
        await ctx.send(embed=embed)

    @commands.command(
        help='Generate a mystery game.  Find a list of weights at https://l.synack.live/weights'
    )
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def mystery(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(weightset=weightset, tournament=tournament, spoilers="mystery")
        embed = await seed.embed(emojis=self.bot.emojis, name="Mystery Race Game")
        await ctx.send(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
