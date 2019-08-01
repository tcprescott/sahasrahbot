from ..database import config, permissions, daily

import discord
from discord.ext import tasks, commands

import bs4
import aiohttp
import re
import asyncio
import html5lib

import aiocache

import pyz3r

def is_daily_channel():
    async def predicate(ctx):
        if ctx.guild == None:
            return False
        result = await config.get_parameter(ctx.guild.id, 'DailyAnnouncerChannel')
        if not result == None:
            channels = result['value'].split(',')
            if ctx.channel.name in channels:
                return True
        return False
    return commands.check(predicate)

class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announce_daily.start()

    @commands.command(
        name='daily',
        brief='Returns the current daily seed.',
        help='Returns the currently daily seed.')
    @is_daily_channel()
    async def daily(self, ctx):
        hash = await find_daily_hash()
        embed = await daily_embed(hash)
        await update_daily(hash)
        await ctx.send(embed=embed)

    @commands.command(
        name='checkdailyannounce'
    )
    @commands.is_owner()
    async def checkdailyannounce(self, ctx):
        await ctx.send(self.announce_daily.failed())

    @tasks.loop(minutes=5, reconnect=True)
    async def announce_daily(self):
        print("announcer running")
        hash = await find_daily_hash()
        if await update_daily(hash):
            embed = await daily_embed(hash)
            daily_announcer_channels = await config.get_all_parameters_by_name('DailyAnnouncerChannel')
            for result in daily_announcer_channels:
                guild = self.bot.get_guild(result['guild_id'])
                for channel_name in result['value'].split(","):
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Daily(bot))

async def update_daily(hash):
    latest_daily = await daily.get_latest_daily()
    if not latest_daily['hash'] == hash:
        print('omg new daily')
        await daily.set_new_daily(hash)
        return True
    else:
        return False

async def daily_embed(hash):
    seed = await get_daily_seed(hash)
    embed = discord.Embed(title=seed.data['spoiler']['meta']['name'], description="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily", color=discord.Colour.blue())
    embed.add_field(name='Logic', value=seed.data['spoiler']['meta']['logic'], inline=True)
    embed.add_field(name='Difficulty', value=seed.data['spoiler']['meta']['difficulty'], inline=True)
    embed.add_field(name='Variation', value=seed.data['spoiler']['meta']['variation'], inline=True)
    embed.add_field(name='State', value=seed.data['spoiler']['meta']['mode'], inline=True)
    embed.add_field(name='Swords', value=seed.data['spoiler']['meta']['weapons'], inline=True)
    embed.add_field(name='Goal', value=seed.data['spoiler']['meta']['goal'], inline=True)
    embed.add_field(name='File Select Code', value=await seed.code(), inline=False)
    embed.add_field(name='Permalink', value=seed.url, inline=False)
    return embed

@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash):
    return await pyz3r.async_alttpr(hash=hash)

# thanks Espeon for this bit of code (it was adapted to use aiohttp instead)
@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://alttpr.com/daily') as resp:
            text = await resp.read()

    html = bs4.BeautifulSoup(text.decode('utf-8'), 'html5lib')
    hash_loader = str(html.find_all('vt-hash-loader')[0])

    regex = re.compile('(hash=")\w{9,10}(")')
    match = regex.search(hash_loader)
    seed = match.group()[6:-1]
    return seed
