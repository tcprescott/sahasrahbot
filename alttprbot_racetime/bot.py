import logging
import os
import ssl
import sys

import aiohttp
from tenacity import RetryError, AsyncRetrying, stop_after_attempt, retry_if_exception_type, wait_exponential

from alttprbot import models
from config import Config as c
from racetime_bot import Bot
# from alttprbot.database import sgl2020_tournament, sgl2020_tournament_bo3

from . import handlers


logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)


logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)

RACETIME_GAMES = os.environ.get('RACETIME_GAMES', '').split(',')
RACETIME_HOST = os.environ.get('RACETIME_HOST', 'racetime.gg')
RACETIME_SECURE = os.environ.get('RACETIME_SECURE', 'true') == 'true'
RACETIME_PORT = os.environ.get('RACETIME_PORT', None)


class SahasrahBotRaceTimeBot(Bot):
    racetime_host = RACETIME_HOST
    racetime_port = RACETIME_PORT
    racetime_secure = RACETIME_SECURE

    def __init__(self, handler_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_class = handler_class
        if self.racetime_secure:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    def get_handler_kwargs(self, ws_conn, state):
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': c.RACETIME_COMMAND_PREFIX,
        }

    def get_handler_class(self):
        return self.handler_class

    async def start(self):
        self.access_token, self.reauthorize_every = await self.authorize()
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())

        unlisted_rooms = await models.RTGGUnlistedRooms.filter(category=self.category_slug)
        for unlisted_room in unlisted_rooms:
            try:
                async for attempt in AsyncRetrying(
                        stop=stop_after_attempt(5),
                        retry=retry_if_exception_type(aiohttp.ClientResponseError)):
                    with attempt:
                        async with self.http.get(
                            self.http_uri(f'/{unlisted_room.room_name}/data'),
                            ssl=self.ssl_context,
                        ) as resp:
                            race_data = await resp.json()

                if race_data['status']['value'] in ['finished', 'cancelled'] or not race_data['unlisted']:
                    await unlisted_room.delete()
                else:
                    await self.join_race_room(unlisted_room.room_name)

            except RetryError as e:
                raise e.last_attempt._exception from e


def start_racetime(loop):
    for bot in racetime_bots.values():
        loop.create_task(bot.start())


racetime_bots = {}
for slug in RACETIME_GAMES:
    stripped_slug = slug.replace('-', '')
    racetime_bots[slug] = SahasrahBotRaceTimeBot(
        category_slug=slug,
        client_id=os.environ.get(f"RACETIME_CLIENT_ID_{stripped_slug.upper()}"),
        client_secret=os.environ.get(
            f'RACETIME_CLIENT_SECRET_{stripped_slug.upper()}'),
        logger=logger,
        handler_class=getattr(handlers, stripped_slug).GameHandler
    )
