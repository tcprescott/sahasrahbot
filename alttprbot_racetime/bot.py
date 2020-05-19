import logging
import websockets
import sys
import ssl

from racetime_bot import Bot

from config import Config as c

from .handler import AlttprHandler

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

    async def start(self):
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())

racetime_alttpr = AlttprBot(
    category_slug='ALttPR',
    client_id=c.RACETIME_CLIENT_ID,
    client_secret=c.RACETIME_CLIENT_SECRET,
    logger=logger,
)
