import asyncio
import logging
import urllib.parse

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from tortoise import Tortoise

import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util.security_validation import run_startup_security_validation
from alttprbot_api.api import sahasrahbotapi
from alttprbot_audit.bot import start_bot as start_audit_bot
from alttprbot_discord.bot import start_bot as start_discord_bot
from alttprbot_racetime.bot import start_racetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        db_url=f'mysql://{config.DB_USER}:{urllib.parse.quote_plus(config.DB_PASS)}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )


if __name__ == '__main__':
    # Run startup security validation before proceeding
    try:
        logger.info("=== Starting SahasrahBot ===")
        security_results = run_startup_security_validation(config)
        logger.info(f"Security validation passed: {security_results}")
    except Exception as e:
        logger.error(f"FATAL: Security validation failed: {e}")
        logger.error("Application startup aborted due to security validation failure")
        exit(1)
    
    loop = asyncio.get_event_loop()

    dbtask = loop.create_task(database())
    loop.run_until_complete(dbtask)

    loop.create_task(start_discord_bot())
    loop.create_task(start_audit_bot())
    start_racetime(loop)
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
