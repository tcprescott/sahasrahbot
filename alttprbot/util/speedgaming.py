import json
import logging
from datetime import timedelta, datetime
from typing import List

import aiofiles
import aiohttp
import pytz

import config
from alttprbot.exceptions import SahasrahBotException


class SGEpisodeNotFoundException(SahasrahBotException):
    pass


class SGEventNotFoundException(SahasrahBotException):
    pass


async def get_upcoming_episodes_by_event(event, hours_past=4, hours_future=4, static_time: datetime=None):
    if config.DEBUG and event == 'test':
        test_schedule = []
        for episode_id in [1]:
            episode = await get_episode(episode_id)
            test_schedule.append(episode)
        return test_schedule

    if static_time:
        now = static_time
    else:
        now = datetime.now(tz=pytz.timezone('US/Eastern'))
    sched_from = now - timedelta(hours=hours_past)
    sched_to = now + timedelta(hours=hours_future)
    params = {
        'event': event,
        'from': sched_from.isoformat(),
        'to': sched_to.isoformat()
    }
    async with aiohttp.request(
            method='get',
            url=f'{config.SG_API_ENDPOINT}/schedule',
            params=params,
    ) as resp:
        schedule: List[dict] = await resp.json(content_type='text/html')
        episode_ids = [episode['id'] for episode in schedule]
        logging.info(
            f'Retrieved schedule for {event} ({resp.status} {resp.reason}).  Received {len(schedule)} matches.  From: {sched_from} To: {sched_to}.  Match IDs: {", ".join(map(str, episode_ids))}')

    if 'error' in schedule:
        raise SGEventNotFoundException(f"Unable to retrieve schedule for {event}. {schedule.get('error')}")

    return schedule


async def get_episode(episodeid: int, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SpeedGaming
    if config.DEBUG:
        if episodeid == 1:
            async with aiofiles.open('test_input/sg_1.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 2 and not complete:
            async with aiofiles.open('test_input/sg_2.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 3 and complete:
            async with aiofiles.open('test_input/sg_3.json', 'r') as f:
                result = json.loads(await f.read(), strict=False)
        elif episodeid == 0:
            result = {"error": "Failed to find episode with id 0."}
        else:
            async with aiohttp.request(
                    method='get',
                    url=f'{config.SG_API_ENDPOINT}/episode',
                    params={'id': episodeid},
            ) as resp:
                result = await resp.json(content_type='text/html')
    else:
        async with aiohttp.request(
                method='get',
                url=f'{config.SG_API_ENDPOINT}/episode',
                params={'id': episodeid},
        ) as resp:
            result = await resp.json(content_type='text/html')

    if 'error' in result:
        raise SGEpisodeNotFoundException(result["error"])

    # if not result['event']['slug'] == 'alttpr':
    #     raise SGEpisodeNotFoundException('Not an alttpr tournament race.')

    return result
