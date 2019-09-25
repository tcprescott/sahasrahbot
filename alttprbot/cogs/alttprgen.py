import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..util import embed_formatter

from ..alttprgen.weights import weights
from ..alttprgen.random import generate_random_game
from ..alttprgen.preset import get_preset

from config import Config as c

import aiohttp
import json


class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def seedgen(self, ctx):
        if ctx.invoked_subcommand is None:
            raise Exception('Try providing a valid subcommand.  Use "$help seedgen" for assistance.')

    @seedgen.command()
    async def custom(self, ctx, tournament: bool = True):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError:
            raise Exception('You must attach a customizer save json file.')

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = customizer.convert2settings(
            customizer_settings, tournament=tournament)

        seed = await pyz3r.alttpr(
            customizer=True,
            baseurl=c.baseurl,
            seed_baseurl=c.seed_baseurl,
            username=c.username,
            password=c.password,
            settings=settings
        )

        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @seedgen.command()
    async def preset(self, ctx, preset):
        seed, goal_name = await get_preset(preset)
        if not seed:
            raise Exception('Could not generate game.  Maybe preset does not exist?')
        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis)
        await ctx.send(embed=embed)


    @seedgen.command()
    async def weightlist(self, ctx):
        w = ''
        for k in weights.keys():
            d = weights[k]['description']
            w += f'{k} - {d}\n'
        await ctx.send('Currently configured weights:\n\n{weights}\n\nCurrent weights of this bot can be found at https://github.com/tcprescott/alttpr-discord-bot/blob/master/alttprbot/alttprgen/weights.py'.format(
            weights=w
        ))

    @seedgen.command()
    @commands.cooldown(rate=3, per=900, type=commands.BucketType.user)
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(logic='NoGlitches', weightset=weightset, tournament=tournament)
        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, name="Random Race Game")
        await ctx.send(embed=embed)


async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)


def setup(bot):
    bot.add_cog(AlttprGen(bot))
