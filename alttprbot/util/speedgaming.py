import json
from datetime import timedelta, datetime

import aiofiles
import aiohttp
import pytz

from alttprbot.exceptions import SahasrahBotException
from config import Config as c


class SGEpisodeNotFoundException(SahasrahBotException):
    pass

class SGEventNotFoundException(SahasrahBotException):
    pass

async def get_upcoming_episodes_by_event(event, hours_past=4, hours_future=4):
    if c.DEBUG and event == 'test':
        test_schedule = []
        for episode_id in [1]:
            episode = await get_episode(episode_id)
            test_schedule.append(episode)
        return test_schedule

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
        url=f'{c.SgApiEndpoint}/schedule',
        params=params,
    ) as resp:
        print(resp.url)
        schedule = await resp.json(content_type='text/html')

    if 'error' in schedule:
        raise SGEventNotFoundException(f"Unable to retrieve schedule for {event}. {schedule.get('error')}")

    return schedule


async def get_episode(episodeid: int, complete=False):
    # if we're developing locally, we want to have some artifical data to use that isn't from SpeedGaming
    if c.DEBUG:
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
                url=f'{c.SgApiEndpoint}/episode',
                params={'id': episodeid},
            ) as resp:
                result = await resp.json(content_type='text/html')
    else:
        async with aiohttp.request(
            method='get',
            url=f'{c.SgApiEndpoint}/episode',
            params={'id': episodeid},
        ) as resp:
            result = await resp.json(content_type='text/html')

    if 'error' in result:
        raise SGEpisodeNotFoundException(result["error"])

    # if not result['event']['slug'] == 'alttpr':
    #     raise SGEpisodeNotFoundException('Not an alttpr tournament race.')

    return result
