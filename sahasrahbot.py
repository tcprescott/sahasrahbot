from dotenv import load_dotenv  # nopep8
load_dotenv()  # nopep8

import asyncio
import os
import urllib.parse

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from tortoise import Tortoise

from alttprbot_api.api import sahasrahbotapi
from alttprbot_discord.bot import discordbot
from alttprbot_audit.bot import discordbot as discordbot_audit
from alttprbot_racetime.bot import start_racetime
# from alttprbot_twitch.bot import twitchbot

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "sahasrahbot")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = urllib.parse.quote_plus(os.environ.get("DB_PASS", "pass"))

if os.environ.get("SENTRY_URL"):
    sentry_sdk.init(
        os.environ.get("SENTRY_URL"),
        integrations=[AioHttpIntegration()]
    )


async def database():
    await Tortoise.init(
        db_url=f'mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    dbtask = loop.create_task(database())
    loop.run_until_complete(dbtask)

    loop.create_task(discordbot.start(os.environ.get("DISCORD_TOKEN")))
    loop.create_task(discordbot_audit.start(os.environ.get("AUDIT_DISCORD_TOKEN")))
    # loop.create_task(twitchbot.start())
    start_racetime(loop)
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
