# This script exists so I can quickly connect to the database using ipython for experimentation.

import asyncio

from tortoise import Tortoise

import settings

async def database():
    await Tortoise.init(
        db_url=f'mysql://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

loop = asyncio.get_event_loop()
dbtask = loop.create_task(database())
loop.run_until_complete(dbtask)
