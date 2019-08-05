import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..database import alttprgen

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
    async def custom(self, ctx, tournament: bool=True):
        try:
            if not ctx.message.attachments[0].filename.endswith('.json'):
                raise Exception('File should have a .json extension.')
        except IndexError:
            raise Exception('You must attach a customizer save json file.')
        
        customizer_settings = await get_customizer_json(ctx.message.attachments[0].url)

        settings = customizer.convert2settings(customizer_settings, tournament=tournament)

        seed = await pyz3r.async_alttpr(
            randomizer='item',
            settings=settings
        )

        embed = await seed_embed(seed)
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

        embed = await seed_embed(seed)
        await ctx.send(embed=embed)

    @seedgen.command()
    async def random(self, ctx, randomizer='random', use_enemizer: bool=True, tournament: bool=True):
        if randomizer not in ['random','item','entrance']:
            raise Exception('randomizer must be random, item, or entrance!')
        seed = await generate_random_game(randomizer=randomizer, use_enemizer=use_enemizer, tournament=tournament)

        embed = await seed_embed(seed)
        await ctx.send(embed=embed)

async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)

async def seed_embed(seed):
    try:
        name = seed.data['spoiler']['meta']['name']
    except KeyError:
        name = 'Requested Seed'
    try:
        notes = seed.data['spoiler']['meta']['notes']
    except KeyError:
        notes = ""

    embed = discord.Embed(title=name, description=notes, color=discord.Colour.dark_red())
    embed.add_field(name='Logic', value=seed.data['spoiler']['meta']['logic'], inline=True)
    embed.add_field(name='Difficulty', value=seed.data['spoiler']['meta']['difficulty'], inline=True)
    embed.add_field(name='Variation', value=seed.data['spoiler']['meta']['variation'], inline=True)
    embed.add_field(name='State', value=seed.data['spoiler']['meta']['mode'], inline=True)

    try:
        embed.add_field(name='Swords', value=seed.data['spoiler']['meta']['weapons'], inline=True)
    except KeyError:
        pass

    try:
        embed.add_field(name='Shuffle', value=seed.data['spoiler']['meta']['shuffle'], inline=True)
    except KeyError:
        pass

    embed.add_field(name='Goal', value=seed.data['spoiler']['meta']['goal'], inline=True)

    try:
        embed.add_field(name='Enemizer Enemy Shuffle', value=seed.data['spoiler']['meta']['enemizer_enemy'], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Shuffle', value=seed.settings['enemizer']['enemy'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Boss Shuffle', value=seed.data['spoiler']['meta']['enemizer_bosses'], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Boss Shuffle', value=seed.settings['enemizer']['bosses'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Pot Shuffle', value=seed.data['spoiler']['meta']['enemizer_pot_shuffle'], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Pot Shuffle', value=seed.settings['enemizer']['pot_shuffle'], inline=True)
        except KeyError:
            pass

    healthmap = {
        0: 'Default',
        1: 'Easy (1-4 hp)',
        2: 'Normal (2-15 hp)',
        3: 'Hard (2-30 hp)',
        4: 'Brick Wall (4-50 hp)'
    }
    try:
        embed.add_field(name='Enemizer Enemy Health', value=healthmap[seed.data['spoiler']['meta']['enemizer_enemy_health']], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Health', value=healthmap[seed.settings['enemizer']['enemy_health']], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Enemy Damage', value=seed.data['spoiler']['meta']['enemizer_enemy_damage'], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Enemy Damage', value=seed.settings['enemizer']['enemy_damage'], inline=True)
        except KeyError:
            pass

    try:
        embed.add_field(name='Enemizer Palette Shuffle', value=seed.data['spoiler']['meta']['enemizer_palette_shuffle'], inline=True)
    except KeyError:
        try:
            if seed.settings['enemizer']: embed.add_field(name='Enemizer Palette Shuffle', value=seed.settings['enemizer']['palette_shuffle'], inline=True)
        except KeyError:
            pass

    embed.add_field(name='File Select Code', value=await seed.code(), inline=False)
    embed.add_field(name='Permalink', value=seed.url, inline=False)
    return embed

async def generate_random_game(logic='NoGlitches', use_enemizer=True, randomizer='random', tournament=True):
    if randomizer == 'random':
        r = random.choices(
            population=['item','entrance'],
            weights=[1,1]
        )[0]
    else:
        r = randomizer

    if r == 'item':
        difficulty = random.choices(
            population=['easy','normal','hard','expert','insane'],
            weights=[.5,1,1,.5,.1]
        )[0]
        goal = random.choices(
            population=['ganon','dungeons','pedestal','triforce-hunt'],
            weights=[1,1,1,1]
        )[0]
        mode = random.choices(
            population=['standard','open','inverted'],
            weights=[1,1,1]
        )[0]
        weapons = random.choices(
            population=['randomized','uncle','swordless'],
            weights=[1,1,1]
        )[0]
        variation = random.choices(
            population=['none','key-sanity','retro'],
            weights=[1,1,.25]
        )[0]

        if use_enemizer:
            enemizer=random_enemizer(mode)
        else:
            enemizer=False
        
        settings={
            "logic":logic,
            "difficulty":difficulty,
            "variation":variation,
            "mode":mode,
            "goal":goal,
            "weapons":weapons,
            "tournament":tournament,
            "spoilers":False,
            "enemizer":enemizer,
            "lang":"en"
        }
        
    elif r == 'entrance':
        difficulty = random.choices(
            population=['easy','normal','hard','expert','insane'],
            weights=[.5,1,1,.5,.1]
        )[0]
        goal = random.choices(
            population=['ganon','crystals','dungeons','pedestal','triforcehunt'],
            weights=[1,1,1,1,1]
        )[0]
        mode = random.choices(
            population=['swordless','open'],
            weights=[1,1]
        )[0]
        shuffle = random.choices(
            population=['simple','restricted','full','crossed','insanity'],
            weights=[.75,.75,1,1,.25]
        )[0]
        variation = random.choices(
            population=['none','key-sanity','retro'],
            weights=[1,1,.25]
        )[0]

        if use_enemizer:
            enemizer=random_enemizer(mode)
        else:
            enemizer=False

        settings={
            "logic":"NoGlitches",
            "difficulty":difficulty,
            "variation":variation,
            "mode":mode,
            "goal":goal,
            "shuffle":shuffle,
            "tournament":tournament,
            "spoilers":False,
            "enemizer":enemizer,
            "lang":"en"
        }
    else:
        raise Exception('randomizer needs to be item or entrance!')

    print(json.dumps(settings, indent=4))
    seed = await pyz3r.async_alttpr(
        randomizer=r,
        settings=settings
    )
    return seed
    
def random_enemizer(mode=None):
    enabled = random.choices(
        population=[True, False],
        weights=[1,1]
    )[0]
    if not enabled:
        return False
    else:
        if mode == 'standard':
            enemy=False
            enemy_health=0
        else:
            enemy = random.choices(
                population=[True, False],
                weights=[1,1]
            )[0]
            enemy_health = random.choices(
                population=[0,1,2,3,4],
                weights=[1,1,1,.25,.1]
            )[0]

        pot_shuffle = random.choices(
            population=[True, False],
            weights=[1,1]
        )[0]
        palette_shuffle = random.choices(
            population=[True, False],
            weights=[1,1]
        )[0]
        enemy_damage = random.choices(
            population=['off','shuffle','chaos'],
            weights=[1,1,1]
        )[0]
        boss = random.choices(
            population=['off','basic','normal','chaos'],
            weights=[1,1,1,1]
        )[0]

        return {
            "enemy":enemy,
            "enemy_health":enemy_health,
            "enemy_damage":enemy_damage,
            "bosses":boss,
            "palette_shuffle":palette_shuffle,
            "pot_shuffle":pot_shuffle
        }

def setup(bot):
    bot.add_cog(AlttprGen(bot))
