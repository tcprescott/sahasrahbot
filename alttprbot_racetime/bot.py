import logging
import ssl
import sys

import websockets

from config import Config as c
from racetime_bot import Bot

from .handler import AlttprHandler
from .handler_smz3 import Smz3Handler

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)

handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(handler)


class AlttprBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl.SSLContext()

    def get_handler_class(self):
        return AlttprHandler

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': c.RACETIME_COMMAND_PREFIX,
        }

    async def start(self):
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())


class Smz3Bot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl.SSLContext()

    def get_handler_class(self):
        return Smz3Handler

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': c.RACETIME_COMMAND_PREFIX,
        }

    async def start(self):
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())


racetime_alttpr = AlttprBot(
    category_slug='ALttPR',
    client_id=c.RACETIME_CLIENT_ID,
    client_secret=c.RACETIME_CLIENT_SECRET,
    logger=logger,
)

racetime_smz3 = Smz3Bot(
    category_slug='smz3',
    client_id=c.RACETIME_CLIENT_ID_SMZ3,
    client_secret=c.RACETIME_CLIENT_SECRET_SMZ3,
    logger=logger
)
