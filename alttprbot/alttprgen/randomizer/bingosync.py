import os
import logging

import aiohttp
from bs4 import BeautifulSoup

from alttprbot.exceptions import SahasrahBotException

BINGOSYNC_BASE_URL = os.environ.get(
    'BINGOSYNC_BASE_URL', 'https://bingosync.com')

jar = aiohttp.CookieJar(unsafe=True)
try:
    jar.load('data/bingosync.cookie')
except FileNotFoundError:
    logging.warning("No bingosync cookie file found.  Will skip loading...")

# WARNING: This is incredibly jank and relies on private endpoints within Bingosync
# that are not intended for public consumption.
# This could break at any time, and it would be our problem, not Bingosync's problem.


async def create_bingo_room(config):
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        try:
            async with session.request(
                method='get',
                url=BINGOSYNC_BASE_URL,
                raise_for_status=True
            ) as resp:
                soup = BeautifulSoup(await resp.text(), features="html5lib")
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
            allow_redirects=False,
            raise_for_status=True,
            data=config
        ) as resp:
            jar.save('data/bingosync.cookie')
            if resp.status == 302:
                return resp.headers['Location'].split("/")[-1]


async def new_card(config):
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        async with session.request(
            method='put',
            url=f"{BINGOSYNC_BASE_URL}/api/new-card",
            raise_for_status=True,
            json=config
        ) as resp:
            return await resp.text()
