import asyncio
import contextlib
import logging
import signal
import urllib.parse

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from tortoise import Tortoise

import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot.util.config_contract import ConfigValidationError, validate_config_contract
from alttprbot_api.api import sahasrahbotapi
from alttprbot_audit.bot import start_bot as start_audit_bot, stop_bot as stop_audit_bot
from alttprbot_discord.bot import start_bot as start_discord_bot, stop_bot as stop_discord_bot

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


async def _cancel_tasks(tasks):
    for task in tasks:
        if not task.done():
            task.cancel()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _graceful_shutdown(service_tasks):
    logger.info('Graceful shutdown started.')

    from alttprbot_racetime.bot import stop_racetime

    with contextlib.suppress(Exception):
        await stop_racetime()

    with contextlib.suppress(Exception):
        await stop_discord_bot()

    with contextlib.suppress(Exception):
        await stop_audit_bot()

    await _cancel_tasks(service_tasks)

    with contextlib.suppress(Exception):
        await Tortoise.close_connections()

    logger.info('Graceful shutdown complete.')


async def _run():
    from alttprbot_racetime.bot import start_racetime

    await database()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def request_shutdown(sig_name):
        logger.info('Received %s, requesting shutdown.', sig_name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, request_shutdown, sig.name)

    service_tasks = [
        asyncio.create_task(start_discord_bot(), name='discord-bot'),
        asyncio.create_task(start_audit_bot(), name='audit-bot'),
        asyncio.create_task(
            sahasrahbotapi.run_task(host='127.0.0.1', port=5001, shutdown_trigger=stop_event.wait),
            name='quart-api',
        ),
    ]
    service_tasks.extend(start_racetime())

    def on_service_done(task):
        if task.cancelled():
            return

        error = task.exception()
        if error is not None:
            logger.error(
                'Service task %s exited with error. Triggering shutdown.',
                task.get_name(),
                exc_info=(type(error), error, error.__traceback__),
            )
            stop_event.set()

    for task in service_tasks:
        task.add_done_callback(on_service_done)

    try:
        await stop_event.wait()
    finally:
        await _graceful_shutdown(service_tasks)


if __name__ == '__main__':
    try:
        validate_config_contract()
    except ConfigValidationError as error:
        raise SystemExit(f'Configuration validation failed: {error}') from error
    asyncio.run(_run())
