import os

import aiohttp
from bs4 import BeautifulSoup

from alttprbot.exceptions import SahasrahBotException

BINGOSYNC_BASE_URL = os.environ.get(
    'RACETIME_BASE_URL', 'https://bingosync.com')

# WARNING: This is incredibly jank and relies on private endpoints within Bingosync
# that are not intended for public consumption.
# This could break at any time, and it would be our problem, not Bingosync's problem.


async def create_bingo_card(config):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method='get',
                url=BINGOSYNC_BASE_URL,
                raise_for_status=True
            ) as resp:
                soup = BeautifulSoup(await resp.text(), features="html5lib")
                cookies = resp.cookies
        except:
            raise SahasrahBotException(
                "Unable to acquire CSRF token.  Please contact Synack for help.")

        csrftoken = soup.find(
            'input', {'name': 'csrfmiddlewaretoken'})['value']

        config['csrfmiddlewaretoken'] = csrftoken

        async with session.request(
            method='post',
            url=BINGOSYNC_BASE_URL,
            headers={'Origin': BINGOSYNC_BASE_URL,
                     'Referer': BINGOSYNC_BASE_URL},
            cookies=cookies,
            allow_redirects=False,
            raise_for_status=True,
            data=config
        ) as resp:
            if resp.status == 302:
                return f"{BINGOSYNC_BASE_URL}{resp.headers['Location']}"
