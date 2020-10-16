import os

import aiohttp
from bs4 import BeautifulSoup

from alttprbot.exceptions import SahasrahBotException

RTGG_SESSION_TOKEN = os.environ.get('RACETIME_SESSION_TOKEN')
RTGG_CSRF_TOKEN = os.environ.get('RACETIME_CSRF_TOKEN')
RTGG_BASE_URL = os.environ.get('RACETIME_BASE_URL', 'https://racetime.gg')

# WARNING: This is incredibly jank and relies on private endpoints within RT.gg
# that are not intended for public consumption.
# This could break at any time, and it would be our problem, not RaceTime's problem.


async def create_race(game, config):
    try:
        async with aiohttp.request(
            method='get',
            url=f'{RTGG_BASE_URL}/{game}/startrace',
            cookies={'sessionid': RTGG_SESSION_TOKEN,
                     'csrftoken': RTGG_CSRF_TOKEN},
            raise_for_status=True
        ) as resp:
            soup = BeautifulSoup(await resp.text(), features="html5lib")
    except:
        raise SahasrahBotException(
            "Unable to acquire CSRF token.  Please contact Synack for help.")

    csrftoken = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

    config['csrfmiddlewaretoken'] = csrftoken
    config['recordable'] = True

    try:
        async with aiohttp.request(
            method='post',
            url=f'{RTGG_BASE_URL}/{game}/startrace',
            cookies={'sessionid': RTGG_SESSION_TOKEN,
                     'csrftoken': RTGG_CSRF_TOKEN},
            headers={'Origin': RTGG_BASE_URL,
                     'Referer': f'{RTGG_BASE_URL}/{game}/startrace'},
            allow_redirects=False,
            data=config
        ) as resp:
            if resp.status == 302:
                return resp.headers['Location']
    except:
        raise SahasrahBotException(
            "Unable to create the race room.  Please contact Synack for help.")
