import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..database import alttprgen
from ..util import embed_formatter

from ..alttprgen.weights import weights

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

        seed = await pyz3r.async_alttpr(
            randomizer='item',
            settings=settings
        )

        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @seedgen.command()
    async def preset(self, ctx, preset):
        result = await alttprgen.get_seed_preset(preset)
        if not len(result):
            raise Exception('Preset not found.')

        seed = await pyz3r.async_alttpr(
            randomizer=result['randomizer'],
            settings=json.loads(result['settings'])
        )

        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis)
        await ctx.send(embed=embed)

    @seedgen.command()
    @commands.is_owner()
    async def savecustomizerpreset(self, ctx, preset):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError:
            raise Exception('You must attach a customizer save json file.')

        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = customizer.convert2settings(
            customizer_settings, tournament=True)
        await alttprgen.put_seed_preset(name=preset, randomizer='item', settings=json.dumps(settings))

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
    async def random(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(logic='NoGlitches', weightset=weightset, tournament=tournament)
        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, name="Random Race Game")
        await ctx.send(embed=embed)

    @seedgen.command()
    async def owgrandom(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(logic='OverworldGlitches', weightset=weightset, tournament=tournament)
        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, name="Random Race Game")
        await ctx.send(embed=embed)

    @seedgen.command()
    async def nologicrandom(self, ctx, weightset='weighted', tournament: bool = True):
        seed = await generate_random_game(logic='None', weightset=weightset, tournament=tournament)
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

    if logic == 'NoGlitches':
        r = random.choices(
            population=list(o['randomizer'].keys()),
            weights=list(o['randomizer'].values())
        )[0]
    else:
        r = 'item'

    if r == 'item':
        difficulty = random.choices(
            population=list(o['difficulty'].keys()),
            weights=list(o['difficulty'].values())
        )[0]
        goal = random.choices(
            population=list(o['goal_item'].keys()),
            weights=list(o['goal_item'].values())
        )[0]
        mode = random.choices(
            population=list(o['mode_item'].keys()),
            weights=list(o['mode_item'].values())
        )[0]
        weapons = random.choices(
            population=list(o['weapons'].keys()),
            weights=list(o['weapons'].values())
        )[0]
        variation = random.choices(
            population=list(o['variation'].keys()),
            weights=list(o['variation'].values())
        )[0]
    elif r == 'entrance':
        difficulty = random.choices(
            population=list(o['difficulty'].keys()),
            weights=list(o['difficulty'].values())
        )[0]
        goal = random.choices(
            population=list(o['goal_entrance'].keys()),
            weights=list(o['goal_entrance'].values())
        )[0]
        mode = random.choices(
            population=list(o['mode_entrance'].keys()),
            weights=list(o['mode_entrance'].values())
        )[0]
        shuffle = random.choices(
            population=list(o['shuffle'].keys()),
            weights=list(o['shuffle'].values())
        )[0]
        variation = random.choices(
            population=list(o['variation'].keys()),
            weights=list(o['variation'].values())
        )[0]
    else:
        raise Exception('randomizer needs to be item or entrance!')

    enemizer = random.choices(
        population=list(o['enemizer_enabled'].keys()),
        weights=list(o['enemizer_enabled'].values())
    )[0]
    if enemizer:
        if mode == 'standard':
            enemy = False
            enemy_health = 0
        else:
            enemy = random.choices(
                population=list(o['enemizer_enemy'].keys()),
                weights=list(o['enemizer_enemy'].values())
            )[0]
            enemy_health = random.choices(
                population=list(o['enemizer_enemy_health'].keys()),
                weights=list(o['enemizer_enemy_health'].values())
            )[0]

        pot_shuffle = random.choices(
            population=list(o['enemizer_pot_shuffle'].keys()),
            weights=list(o['enemizer_pot_shuffle'].values())
        )[0]
        palette_shuffle = random.choices(
            population=list(o['enemizer_palette_shuffle'].keys()),
            weights=list(o['enemizer_palette_shuffle'].values())
        )[0]
        enemy_damage = random.choices(
            population=list(o['enemizer_enemy_damage'].keys()),
            weights=list(o['enemizer_enemy_damage'].values())
        )[0]
        boss = random.choices(
            population=list(o['enemizer_boss'].keys()),
            weights=list(o['enemizer_boss'].values())
        )[0]

        enemizer = {
            "enemy": enemy,
            "enemy_health": enemy_health,
            "enemy_damage": enemy_damage,
            "bosses": boss,
            "palette_shuffle": palette_shuffle,
            "pot_shuffle": pot_shuffle
        }

    if r == 'item':
        settings = {
            "logic": logic,
            "difficulty": difficulty,
            "variation": variation,
            "mode": mode,
            "goal": goal,
            "weapons": weapons,
            "tournament": tournament,
            "spoilers": False,
            "enemizer": enemizer,
            "lang": "en"
        }
    elif r == 'entrance':
        settings = {
            "logic": "NoGlitches",
            "difficulty": difficulty,
            "variation": variation,
            "mode": mode,
            "goal": goal,
            "shuffle": shuffle,
            "tournament": tournament,
            "spoilers": False,
            "enemizer": enemizer,
            "lang": "en"
        }
    else:
        raise Exception('randomizer needs to be item or entrance!')

    # print(json.dumps(settings, indent=4))
    seed = await pyz3r.async_alttpr(
        randomizer=r,
        settings=settings
    )
    return seed


def setup(bot):
    bot.add_cog(AlttprGen(bot))
