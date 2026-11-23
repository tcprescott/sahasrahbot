"""The alttpr.com daily challenge.

``check_for_new_daily`` used to be a ``discord.ext.tasks`` loop in
``alttprbot_discord/cogs/daily.py``. It records each new daily and publishes
``DailyChallengeAvailable``; the Discord announcement is a subscriber.
"""
import logging

import aiocache
import aiohttp

from alttprbot import events, models

logger = logging.getLogger(__name__)


@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def find_daily_hash():
    async with aiohttp.request(method='get', url='https://alttpr.com/api/daily', raise_for_status=True) as resp:
        return await resp.json()


async def update_daily(hash_id) -> bool:
    """Record ``hash_id`` as a daily. Returns True if it hadn't been seen before."""
    current_daily = await models.Daily.filter(hash=hash_id).order_by('-id').first().values()
    if not current_daily:
        logger.info('omg new daily')
        await models.Daily.create(hash=hash_id)
        return True
    else:
        return False


async def check_for_new_daily() -> None:
    daily_challenge = await find_daily_hash()
    hash_id = daily_challenge['hash']
    if await update_daily(hash_id):
        events.publish(events.DailyChallengeAvailable(hash_id=hash_id))
