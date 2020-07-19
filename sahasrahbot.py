import asyncio
import os

import sentry_sdk

from alttprbot.util import orm
from config import Config as c
from alttprbot_discord.bot import discordbot
from alttprbot_srl.bot import srlbot
from alttprbot_twitch.bot import twitchbot
from alttprbot_api.api import sahasrahbotapi
from alttprbot_racetime.bot import racetime_alttpr, racetime_smz3

if os.environ.get("SENTRY_URL", None):
    sentry_sdk.init(os.environ.get("SENTRY_URL"))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(c.DISCORD_TOKEN))
    loop.create_task(srlbot.connect('irc.speedrunslive.com'))
    loop.create_task(twitchbot.start())
    loop.create_task(racetime_alttpr.start())
    loop.create_task(racetime_smz3.start())
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
