import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..database import alttprgen
from ..util import embed_formatter

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
    async def random(self, ctx, randomizer='random', use_enemizer: bool=True, tournament: bool=True):
        if randomizer not in ['random','item','entrance']:
            raise Exception('randomizer must be random, item, or entrance!')
        seed = await generate_random_game(randomizer=randomizer, use_enemizer=use_enemizer, tournament=tournament)

        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, name="Random Race Game")
        await ctx.send(embed=embed)

async def get_customizer_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.read()

    return json.loads(text)

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
            weights=[.25,1,1,.5,.1]
        )[0]
        goal = random.choices(
            population=['ganon','dungeons','pedestal','triforce-hunt'],
            weights=[1,1,1,1]
        )[0]
        mode = random.choices(
            population=['standard','open','inverted'],
            weights=[1,1,.75]
        )[0]
        weapons = random.choices(
            population=['randomized','uncle','swordless'],
            weights=[.4,.4,.2]
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
            weights=[.25,1,1,.5,.1]
        )[0]
        goal = random.choices(
            population=['ganon','crystals','dungeons','pedestal','triforcehunt'],
            weights=[1,1,1,1,1]
        )[0]
        mode = random.choices(
            population=['swordless','open'],
            weights=[.2,.8]
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
        weights=[.75,1]
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
                weights=[1,1,1,.5,.25]
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
            weights=[1,1,.5]
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
