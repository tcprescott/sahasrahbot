import discord
from discord.ext import commands

import pyz3r
from pyz3r.customizer import customizer

from ..database import alttprgen

import aiohttp
import json

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
    embed.add_field(name='Swords', value=seed.data['spoiler']['meta']['weapons'], inline=True)
    embed.add_field(name='Goal', value=seed.data['spoiler']['meta']['goal'], inline=True)
    embed.add_field(name='File Select Code', value=await seed.code(), inline=False)
    embed.add_field(name='Permalink', value=seed.url, inline=False)
    return embed

def setup(bot):
    bot.add_cog(AlttprGen(bot))
