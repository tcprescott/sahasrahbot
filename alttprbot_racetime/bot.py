import json
import logging
import os
import ssl
import sys
from functools import partial

import aiohttp
import requests
from config import Config as c
from racetime_bot import Bot

from .handler import AlttprHandler
from .handler_sgl import SGLHandler
from .handler_smz3 import Smz3Handler

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)


logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)


class SahasrahBotRaceTimeBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl.SSLContext()

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
            raise_for_status=True
        ) as resp:
            race_data = json.loads(await resp.read())

        handler = self.create_handler(race_data)
        name = race_data.get('name')

        self.handlers[name] = self.loop.create_task(handler.handle())
        self.handlers[name].add_done_callback(partial(done, name))

        return race_data

    async def start(self):
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())


class AlttprBot(SahasrahBotRaceTimeBot):
    def get_handler_class(self):
        return AlttprHandler


class Smz3Bot(SahasrahBotRaceTimeBot):
    def get_handler_class(self):
        return Smz3Handler


class SGLBot(SahasrahBotRaceTimeBot):
    def get_handler_class(self):
        return SGLHandler


try:
    racetime_alttpr = AlttprBot(
        category_slug='ALttPR',
        client_id=c.RACETIME_CLIENT_ID,
        client_secret=c.RACETIME_CLIENT_SECRET,
        logger=logger,
    )
except requests.exceptions.HTTPError:
    logger.warning('Unable to authorize alttpr.')
    racetime_alttpr = None

try:
    racetime_smz3 = Smz3Bot(
        category_slug='smz3',
        client_id=c.RACETIME_CLIENT_ID_SMZ3,
        client_secret=c.RACETIME_CLIENT_SECRET_SMZ3,
        logger=logger
    )
except requests.exceptions.HTTPError:
    logger.warning('Unable to authorize smz3.')
    racetime_smz3 = None

if os.environ.get('RACETIME_CLIENT_ID_SGL', None):
    try:
        racetime_sgl = SGLBot(
            category_slug='sgl',
            client_id=os.environ.get('RACETIME_CLIENT_ID_SGL'),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SGL'),
            logger=logger
        )
    except requests.exceptions.HTTPError:
        logger.warning('Unable to authorize sgl.')
        racetime_sgl = None
else:
    racetime_sgl = None
