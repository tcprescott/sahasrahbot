import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..database import alttprgen
from ..util import embed_formatter

from ..alttprgen.weights import weights

from config import Config as c

import aiohttp
import json

import random


class AlttprGen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def seedgen(self, ctx):
        pass

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
        result = await alttprgen.get_seed_preset(preset)
        if not len(result):
            raise Exception('Preset not found.')

        seed = await pyz3r.alttpr(
            customizer=True if result['customizer'] == 1 else False,
            baseurl=c.baseurl,
            seed_baseurl=c.seed_baseurl,
            username=c.username,
            password=c.password,
            settings=json.loads(result['settings'])
        )

        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @seedgen.command()
    @commands.is_owner()
    async def savepreset(self, ctx, preset):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError:
            raise Exception('You must attach a customizer save json file.')

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = customizer.convert2settings(
            customizer_settings, tournament=True)
        await alttprgen.put_seed_preset(name=preset, customizer=1, settings=json.dumps(settings))

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


async def generate_random_game(logic='NoGlitches', weightset='weighted', tournament=True):
    try:
        if weightset == 'casual':
            o = weights['friendly']
        else:
            o = weights[weightset]
    except KeyError:
        raise Exception('Invalid weightset chosen.')

    settings={
        "glitches": get_random_option(o['glitches_required']),
        "item_placement": get_random_option(o['item_placement']),
        "dungeon_items": get_random_option(o['dungeon_items']),
        "accessibility": get_random_option(o['accessibility']),
        "goal": get_random_option(o['goals']),
        "crystals": {
            "ganon": get_random_option(o['tower_open']),
            "tower": get_random_option(o['ganon_open']),
        },
        "mode": get_random_option(o['world_state']),
        "entrances": get_random_option(o['entrance_shuffle']),
        "hints": get_random_option(o['hints']),
        "weapons": get_random_option(o['weapons']),
        "item": {
            "pool": get_random_option(o['item_pool']),
            "functionality": get_random_option(o['item_functionality']),
        },
        "tournament": tournament,
        "spoilers": False,
        "lang": "en",
        "enemizer": {
            "boss_shuffle": get_random_option(o['boss_shuffle']),
            "enemy_shuffle": get_random_option(o['enemy_shuffle']),
            "enemy_damage": get_random_option(o['enemy_damage']),
            "enemy_health": get_random_option(o['enemy_health']),
        }
    }


    # print(json.dumps(settings, indent=4))
    seed = await pyz3r.alttpr(
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password,
        settings=settings
    )
    return seed

def get_random_option(optset):
    return random.choices(population=list(optset.keys()),weights=list(optset.values()))[0]

def setup(bot):
    bot.add_cog(AlttprGen(bot))
