import asyncio
import urllib.parse

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from tortoise import Tortoise

import config
from alttprbot.exceptions import SahasrahBotException
from alttprbot.services import scheduled_jobs
from alttprbot.services.scheduler import Scheduler
from alttprbot_api.api import sahasrahbotapi
from alttprbot_discord import scheduled_job_notifications
from alttprbot_discord.bot import discordbot, start_bot as start_discord_bot
from alttprbot_racetime.bot import start_racetime

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
        db_url=f'mysql://{config.DB_USER}:{urllib.parse.quote(config.DB_PASS, safe="")}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}',
        modules={'models': ['alttprbot.models']},
        # Return timezone-aware UTC datetimes, which is what Tortoise 0.21 did in practice.
        use_tz=True,
        timezone='UTC',
        # Tortoise 1.x keeps ORM state in a context var. The bots and the API query
        # from other tasks, so expose this context globally.
        _enable_global_fallback=True,
    )


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    dbtask = loop.create_task(database())
    loop.run_until_complete(dbtask)

    # Periodic jobs run here, not in Discord cogs. They publish events, and the Discord
    # subscribers registered first turn those into messages once the bot is ready.
    scheduled_job_notifications.register(discordbot)
    scheduler = Scheduler()
    scheduled_jobs.register_jobs(
        scheduler,
        tournament_ready=lambda: scheduled_job_notifications.wait_until_ready(discordbot),
    )
    loop.call_soon(scheduler.start)

    loop.create_task(start_discord_bot())
    # The audit bot is off by default while its privileged intents are unavailable.
    # Set AUDIT_BOT_ENABLED = True in config.py to start it again.
    if getattr(config, 'AUDIT_BOT_ENABLED', False):
        from alttprbot_audit.bot import start_bot as start_audit_bot
        loop.create_task(start_audit_bot())
    start_racetime(loop)
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))
    loop.run_forever()
