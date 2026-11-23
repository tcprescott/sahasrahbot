import aiocache
import discord
from discord import app_commands
from discord.ext import commands

from alttprbot.services.daily import find_daily_hash
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(description='Returns the current daily game from alttpr.com.')
    async def dailygame(self, interaction: discord.Interaction):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        seed = await get_daily_seed(hash_id)
        embed = await seed.embed(emojis=self.bot.emojis,
                                 notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Daily(bot))


@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash_id):
    return await ALTTPRDiscord.retrieve(hash_id=hash_id)
