from dotenv import load_dotenv  # nopep8
load_dotenv()  # nopep8

import asyncio
import os

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from alttprbot.util import orm
from alttprbot_api.api import sahasrahbotapi
from alttprbot_discord.bot import discordbot
from alttprbot_racetime.bot import racetime_alttpr, racetime_smz3
from alttprbot_srl.bot import srlbot
from alttprbot_twitch.bot import twitchbot

if os.environ.get("SENTRY_URL"):
    sentry_sdk.init(
        os.environ.get("SENTRY_URL"),
        integrations=[AioHttpIntegration()]
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(orm.create_pool(loop))
    loop.create_task(discordbot.start(os.environ.get("DISCORD_TOKEN")))
    loop.create_task(twitchbot.start())
    loop.create_task(racetime_alttpr.start())
    loop.create_task(racetime_smz3.start())
    loop.create_task(srlbot.connect('irc.speedrunslive.com'))
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1',
                                        port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
