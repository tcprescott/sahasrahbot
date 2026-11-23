# This script exists so I can quickly connect to the database using ipython for experimentation.

import asyncio
import urllib.parse

from tortoise import Tortoise

import config


async def database():
    await Tortoise.init(
        db_url=f'mysql://{config.DB_USER}:{urllib.parse.quote(config.DB_PASS, safe="")}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']},
        # Return timezone-aware UTC datetimes, which is what Tortoise 0.21 did in practice.
        use_tz=True,
        timezone='UTC',
        # Tortoise 1.x keeps ORM state in a context var. The bots and the API query
        # from other tasks, so expose this context globally.
        _enable_global_fallback=True,
    )


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
dbtask = loop.create_task(database())
loop.run_until_complete(dbtask)
