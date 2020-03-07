import aiocache
import discord
from discord.ext import commands, tasks

from alttprbot.util import http

from ..util.alttpr_discord import alttpr


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announce_daily.start()

    @commands.command(
        name='daily',
        brief='Returns the current daily seed.',
        help='Returns the currently daily seed.')
    async def daily(self, ctx):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        seed = await get_daily_seed(hash_id)
        embed = await seed.embed(emojis=self.bot.emojis, notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        await update_daily(hash_id)
        await ctx.send(embed=embed)


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
                    channel = discord.utils.get(
                        guild.text_channels, name=channel_name)
                    await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Daily(bot))


async def update_daily(hash_id):
    return False


@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash_id):
    return await alttpr(hash_id=hash_id)

@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    return await http.request_generic('https://alttpr.com/api/daily', returntype='json')
