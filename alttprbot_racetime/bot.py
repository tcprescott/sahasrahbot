import json
import logging
import os
import ssl
import sys
from functools import partial

import aiohttp
from config import Config as c
from racetime_bot import Bot

from . import handlers

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

        return race_data

    def get_handler_class(self):
        return self.handler_class

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
