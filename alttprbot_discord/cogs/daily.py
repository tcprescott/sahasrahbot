import logging
import asyncio

import aiocache
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from alttprbot import models
from alttprbot_discord.util.alttpr_discord import ALTTPRDiscord
from alttprbot_discord.util.guild_config_service import GuildConfigService

logger = logging.getLogger(__name__)


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.config_service = GuildConfigService()
        self.announce_daily.start() # pylint: disable=no-member

    @app_commands.command(description='Returns the current daily game from alttpr.com.')
    async def dailygame(self, interaction: discord.Interaction):
        try:
            daily_challenge = await find_daily_hash_with_retry()
            hash_id = daily_challenge.get('hash')
            if not hash_id:
                raise ValueError('Daily challenge payload missing hash')
            seed = await get_daily_seed_with_retry(hash_id)
            embed = await seed.embed(emojis=self.bot.emojis,
                                     notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
            await interaction.response.send_message(embed=embed)
        except (aiohttp.ClientError, ValueError, KeyError, TypeError, RuntimeError) as error:  # noqa: BLE001
            logger.error('Failed to fetch daily challenge for slash command: %s', error)
            await interaction.response.send_message(
                'Unable to fetch the daily challenge right now. Please try again shortly.',
                ephemeral=True
            )

    @tasks.loop(minutes=5, reconnect=True)
    async def announce_daily(self):
        try:
            daily_challenge = await find_daily_hash_with_retry()
            hash_id = daily_challenge.get('hash')
            if not hash_id:
                logger.warning('Daily challenge payload missing hash; skipping tick')
                return

            if not await update_daily(hash_id):
                return

            seed = await get_daily_seed_with_retry(hash_id)
            embed = await seed.embed(emojis=self.bot.emojis,
                                     notes="This is today's daily challenge.  The latest challenge can always be found at https://alttpr.com/daily")
        except (aiohttp.ClientError, ValueError, KeyError, TypeError, RuntimeError) as error:  # noqa: BLE001
            logger.error('Failed daily announcement preparation: %s', error)
            return
        try:
            daily_announcer_channels = await self.config_service.get_all_guilds_with_parameter('DailyAnnouncerChannel')
            for result in daily_announcer_channels:
                guild_id = result.get('guild_id')
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    logger.warning('Guild %s no longer available for daily announcements', guild_id)
                    continue

                channel_ids = await self.config_service.get_channel_ids(
                    guild_id,
                    'DailyAnnouncerChannel',
                    guild
                )

                for channel_id in channel_ids:
                    channel = guild.get_channel(channel_id)
                    if not channel or not isinstance(channel, discord.TextChannel):
                        logger.warning('Daily channel %s invalid in guild %s', channel_id, guild.id)
                        continue

                    try:
                        message: discord.Message = await channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        logger.warning('Missing permissions to send daily to channel %s in guild %s', channel_id, guild.id)
                        continue
                    except discord.HTTPException as error:  # noqa: BLE001
                        logger.error('Error sending daily to channel %s in guild %s: %s', channel_id, guild.id, error)
                        continue

                    thread_name = _daily_thread_name(seed)
                    if not thread_name:
                        continue

                    try:
                        await message.create_thread(
                            name=thread_name,
                            auto_archive_duration=1440
                        )
                    except discord.errors.Forbidden:
                        logger.warning('Missing permissions to create daily thread in channel %s (guild %s)', channel_id, guild.id)
                    except discord.HTTPException as error:  # noqa: BLE001
                        logger.warning('Daily post succeeded but thread creation failed in channel %s (guild %s): %s', channel_id, guild.id, error)
        except Exception:
            logger.exception('Unhandled error in announce_daily loop')

    @announce_daily.error
    async def announce_daily_error(self, error: Exception):
        if isinstance(error, asyncio.CancelledError):
            return
        logger.error('Unhandled exception in announce_daily loop', exc_info=error)
        if not self.announce_daily.is_being_cancelled() and not self.announce_daily.is_running():
            self.announce_daily.restart()

    @announce_daily.before_loop
    async def before_create_races(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Daily(bot))


async def update_daily(hash_id):
    current_daily_exists = await models.Daily.filter(hash=hash_id).exists()
    if not current_daily_exists:
        logger.info('Detected new daily hash %s', hash_id)
        await models.Daily.create(hash=hash_id)
        return True

    return False


@aiocache.cached(ttl=86400, cache=aiocache.SimpleMemoryCache)
async def get_daily_seed(hash_id):
    return await ALTTPRDiscord.retrieve(hash_id=hash_id)


@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    async with aiohttp.request(method='get', url='https://alttpr.com/api/daily', raise_for_status=True) as resp:
        return await resp.json()


@retry(
    retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True
)
async def find_daily_hash_with_retry():
    return await find_daily_hash()


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True
)
async def get_daily_seed_with_retry(hash_id):
    return await get_daily_seed(hash_id)


def _daily_thread_name(seed):
    spoiler = getattr(seed, 'data', {}).get('spoiler', {}) if getattr(seed, 'data', None) else {}
    meta = spoiler.get('meta', {}) if isinstance(spoiler, dict) else {}
    thread_name = meta.get('name') if isinstance(meta, dict) else None
    if isinstance(thread_name, str) and thread_name.strip():
        return thread_name.strip()
    return None
