import asyncio

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from tortoise import Tortoise

from alttprbot_api.api import sahasrahbotapi
from alttprbot_discord.bot import start_bot as start_discord_bot
from alttprbot_audit.bot import start_bot as start_audit_bot
from alttprbot_racetime.bot import start_racetime
from alttprbot.exceptions import SahasrahBotException

import config

if config.SENTRY_URL:
    def before_send(event, hint):
        if 'exc_info' in hint:
            _, exc_value, _ = hint['exc_info']
            if isinstance(exc_value, (SahasrahBotException)):
                return None
        return event

    sentry_sdk.init(
        config.SENTRY_URL,
        integrations=[AioHttpIntegration()],
        before_send=before_send
    )


async def database():
    await Tortoise.init(
        db_url=f'mysql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    dbtask = loop.create_task(database())
    loop.run_until_complete(dbtask)

    loop.create_task(start_discord_bot())
    loop.create_task(start_audit_bot())
    start_racetime(loop)
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
