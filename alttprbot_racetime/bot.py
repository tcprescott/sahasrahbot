import asyncio
import json
import logging
import os
import ssl
import sys
from functools import partial

import aiohttp
from aiohttp.client_exceptions import ClientResponseError
from tenacity import RetryError, AsyncRetrying, stop_after_attempt, retry_if_exception_type
from bs4 import BeautifulSoup
from config import Config as c
from racetime_bot import Bot

from . import handlers

RTGG_SESSION_TOKEN = os.environ.get('RACETIME_SESSION_TOKEN')
RTGG_BASE_URL = os.environ.get('RACETIME_BASE_URL', 'https://racetime.gg')

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)


logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)

RACETIME_GAMES = ['alttpr', 'smz3', 'sgl', 'ff1r', 'z1r', 'smb3r', 'smr']


class SahasrahBotRaceTimeBot(Bot):
    def __init__(self, handler_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_class = handler_class
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': c.RACETIME_COMMAND_PREFIX,
        }

    async def create_handler_by_room_name(self, room_name):
        def done(task_name, *args):
            del self.handlers[task_name]

        async with aiohttp.request(
                method='get',
                url=self.http_uri(f'{room_name}/data'),
                raise_for_status=True) as resp:
            race_data = json.loads(await resp.read())

        handler = self.create_handler(race_data)
        name = race_data.get('name')

        self.handlers[name] = self.loop.create_task(handler.handle())
        self.handlers[name].add_done_callback(partial(done, name))

        count = 0
        while handler.ws is None:
            await asyncio.sleep(1)
            count += 1
            if count > 30:
                raise Exception(
                    "Bot took too long to establish connection with room websocket.")

        return handler

    def get_handler_class(self):
        return self.handler_class

    async def create_race(self, config):
        try:
            async for attempt in AsyncRetrying(stop=stop_after_attempt(5), retry=retry_if_exception_type(ClientResponseError)):
                with attempt:
                    async with aiohttp.request(
                        method='get',
                        url=f'{RTGG_BASE_URL}/{self.category_slug}/startrace',
                        cookies={'sessionid': RTGG_SESSION_TOKEN},
                        raise_for_status=True
                    ) as resp:
                        soup = BeautifulSoup(await resp.text(), features="html5lib")
                        cookies = resp.cookies
        except RetryError as e:
            raise e.last_attempt._exception from e

        csrftoken = soup.find(
            'input', {'name': 'csrfmiddlewaretoken'})['value']

        config['csrfmiddlewaretoken'] = csrftoken
        config['recordable'] = True

        # if we're developing locally, always make the race unlisted to keep things tidy to users
        if c.DEBUG:
            config['unlisted'] = 'on'

        cookies['sessionid'] = RTGG_SESSION_TOKEN

        try:
            async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(ClientResponseError)):
                with attempt:
                    async with aiohttp.request(
                        method='post',
                        url=f'{RTGG_BASE_URL}/{self.category_slug}/startrace',
                        cookies=cookies,
                        headers={'Origin': RTGG_BASE_URL,
                                 'Referer': f'{RTGG_BASE_URL}/{self.category_slug}/startrace'},
                        allow_redirects=False,
                        raise_for_status=True,
                        data=config
                    ) as resp:
                        if resp.status == 302:
                            room_path = resp.headers['Location']
        except RetryError as e:
            raise e.last_attempt._exception from e

        race_handler = await self.create_handler_by_room_name(room_path)

        return race_handler

    async def start(self):
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())


def start_racetime(loop):
    for bot in racetime_bots.values():
        loop.create_task(bot.start())


racetime_bots = {}
for slug in RACETIME_GAMES:
    racetime_bots[slug] = SahasrahBotRaceTimeBot(
        category_slug=slug,
        client_id=os.environ.get(f'RACETIME_CLIENT_ID_{slug.upper()}'),
        client_secret=os.environ.get(f'RACETIME_CLIENT_SECRET_{slug.upper()}'),
        logger=logger,
        handler_class=getattr(handlers, slug).GameHandler
    )
