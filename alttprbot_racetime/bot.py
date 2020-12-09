import logging
import os
import ssl
import sys

from config import Config as c
from racetime_bot import Bot
# from alttprbot.database import sgl2020_tournament, sgl2020_tournament_bo3

from . import handlers

RTGG_SESSION_TOKEN = os.environ.get('RACETIME_SESSION_TOKEN')
RTGG_BASE_URL = os.environ.get('RACETIME_BASE_URL', 'https://racetime.gg')

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)


logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)

RACETIME_GAMES = ['alttpr', 'smz3', 'ff1r', 'z1r', 'smb3r', 'smr', 'z2r']


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

    def get_handler_class(self):
        return self.handler_class

    async def start(self):
        self.access_token, self.reauthorize_every = await self.authorize()
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())


# class SGLRaceTimeBot(SahasrahBotRaceTimeBot):
#     async def start(self):
#         self.loop.create_task(self.reauthorize())
#         self.loop.create_task(self.refresh_races())

#         races = await sgl2020_tournament.get_unrecorded_races()
#         for race in races:
#             if race['platform'] == 'racetime':
#                 if race['room_name'] is None:
#                     continue
#                 await self.create_handler_by_room_name(f"/{race['room_name']}")

#         races_bo3 = await sgl2020_tournament_bo3.get_unrecorded_races()
#         for race in races_bo3:
#             if race['platform'] == 'racetime':
#                 if race['room_name'] is None:
#                     continue
#                 await self.create_handler_by_room_name(f"/{race['room_name']}")

def start_racetime(loop):
    for bot in racetime_bots.values():
        loop.create_task(bot.start())


racetime_bots = {}
for slug in RACETIME_GAMES:
    # if slug == 'sgl':
    racetime_bots[slug] = SahasrahBotRaceTimeBot(
        category_slug=slug,
        client_id=os.environ.get(f'RACETIME_CLIENT_ID_{slug.upper()}'),
        client_secret=os.environ.get(
            f'RACETIME_CLIENT_SECRET_{slug.upper()}'),
        logger=logger,
        handler_class=getattr(handlers, slug).GameHandler
    )
    # else:
    #     racetime_bots[slug] = SGLRaceTimeBot(
    #         category_slug=slug,
    #         client_id=os.environ.get(f'RACETIME_CLIENT_ID_{slug.upper()}'),
    #         client_secret=os.environ.get(
    #             f'RACETIME_CLIENT_SECRET_{slug.upper()}'),
    #         logger=logger,
    #         handler_class=getattr(handlers, slug).GameHandler
    #     )
