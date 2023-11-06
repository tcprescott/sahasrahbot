# This script exists so I can quickly connect to the database using ipython for experimentation.

import asyncio
import urllib.parse

from tortoise import Tortoise

import config


async def database():
    await Tortoise.init(
        db_url=f'mysql://{config.DB_USER}:{urllib.parse.quote_plus(config.DB_PASS)}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

loop = asyncio.get_event_loop()
dbtask = loop.create_task(database())
loop.run_until_complete(dbtask)
