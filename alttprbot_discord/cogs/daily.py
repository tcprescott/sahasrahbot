import aiocache
import aiohttp
import discord
from discord.ext import commands, tasks
import logging

from alttprbot import models
from alttprbot.database import config

from ..util.alttpr_discord import ALTTPRDiscord


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
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        seed = await get_daily_seed(hash_id)
        embed = await seed.embed(emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        await update_daily(hash_id)
        await ctx.reply(embed=embed)

    @commands.slash_command(name='dailygame', description='Returns the current daily game from alttpr.com.')
    async def daily_cmd(self, ctx):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        seed = await get_daily_seed(hash_id)
        embed = await seed.embed(emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        await ctx.respond(embed=embed)

    @tasks.loop(minutes=5, reconnect=True)
    async def announce_daily(self):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        if await update_daily(hash_id):
            seed = await get_daily_seed(hash_id)
            embed = await seed.embed(emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
            daily_announcer_channels = await config.get_all_parameters_by_name('DailyAnnouncerChannel')
            for result in daily_announcer_channels:
                guild = self.bot.get_guild(result['guild_id'])
                for channel_name in result['value'].split(","):
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    message: discord.Message = await channel.send(embed=embed)
                    await message.create_thread(name=seed.data['spoiler']['meta'].get('name'), auto_archive_duration=1440)

    @announce_daily.before_loop
    async def before_create_races(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Daily(bot))


async def update_daily(hash_id):
    current_daily = await models.Daily.filter(hash=hash_id).order_by('-id').first().values()
    if not current_daily:
        logging.info('omg new daily')
        await models.Daily.create(hash=hash_id)
        return True
    else:
        return False


@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash_id):
    return await ALTTPRDiscord.retrieve(hash_id=hash_id)


@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    async with aiohttp.request(method='get', url='https://alttpr.com/api/daily', raise_for_status=True) as resp:
        return await resp.json()
