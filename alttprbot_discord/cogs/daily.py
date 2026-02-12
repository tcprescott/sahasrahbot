import logging

import aiocache
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from alttprbot import models
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.guild_config_service import GuildConfigService


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.config_service = GuildConfigService()
        self.announce_daily.start() # pylint: disable=no-member

    @app_commands.command(description='Returns the current daily game from alttpr.com.')
    async def dailygame(self, interaction: discord.Interaction):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        seed = await get_daily_seed(hash_id)
        embed = await seed.embed(emojis=self.bot.emojis,
                                 notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=5, reconnect=True)
    async def announce_daily(self):
        daily_challenge = await find_daily_hash()
        hash_id = daily_challenge['hash']
        if await update_daily(hash_id):
            seed = await get_daily_seed(hash_id)
            embed = await seed.embed(emojis=self.bot.emojis,
                                     notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
            
            # Use GuildConfigService to fetch daily announcer channels
            daily_announcer_channels = await models.Config.filter(parameter='DailyAnnouncerChannel')
            for result in daily_announcer_channels:
                guild = self.bot.get_guild(result.guild_id)
                if not guild:
                    continue
                
                # Get channel IDs with backward compatibility for channel names
                channel_ids = await self.config_service.get_channel_ids(
                    result.guild_id,
                    'DailyAnnouncerChannel',
                    guild
                )
                
                for channel_id in channel_ids:
                    channel = guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        try:
                            message: discord.Message = await channel.send(embed=embed)
                            await message.create_thread(
                                name=seed.data['spoiler']['meta'].get('name'),
                                auto_archive_duration=1440
                            )
                        except discord.errors.Forbidden:
                            logging.warning(f'Missing permissions to send daily to channel {channel_id} in guild {guild.id}')
                        except Exception as e:
                            logging.error(f'Error sending daily to channel {channel_id} in guild {guild.id}: {e}')

    @announce_daily.before_loop
    async def before_create_races(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Daily(bot))


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
