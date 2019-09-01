from ..database import config, permissions, daily
from ..util import embed_formatter

import discord
from discord.ext import tasks, commands

from config import Config as c

import bs4
import aiohttp
import re
import asyncio
import html5lib

import aiocache

import pyz3r


def is_daily_channel():
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        result = await config.get_parameter(ctx.guild.id, 'DailyAnnouncerChannel')
        if result is not None:
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
        seed = await get_daily_seed(hash)
        embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
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
            seed = await get_daily_seed(hash)
            embed = await embed_formatter.seed_embed(seed, emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
            daily_announcer_channels = await config.get_all_parameters_by_name('DailyAnnouncerChannel')
            for result in daily_announcer_channels:
                guild = self.bot.get_guild(result['guild_id'])
                for channel_name in result['value'].split(","):
                    channel = discord.utils.get(
                        guild.text_channels, name=channel_name)
                    await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Daily(bot))


async def update_daily(gamehash):
    latest_daily = await daily.get_latest_daily()
    if not latest_daily['hash'] == gamehash:
        print('omg new daily')
        await daily.set_new_daily(gamehash)
        return True
    else:
        return False


@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash):
    return await pyz3r.alttpr(
        hash=hash
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password
    )

@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    website = await pyz3r.alttpr(
        baseurl=c.baseurl,
        seed_baseurl=c.seed_baseurl,
        username=c.username,
        password=c.password
    )
    return await website.find_daily_hash()
