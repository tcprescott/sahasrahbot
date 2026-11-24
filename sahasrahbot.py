import asyncio
import urllib.parse

import config
from alttprbot.observability import runtime as observability_runtime
from alttprbot.observability import sentry as observability
from alttprbot.observability import watchdog as observability_watchdog

# Before the bots and the web app are built, so Sentry's integrations wrap them.
# Does nothing without config.SENTRY_URL.
observability.init_sentry()

from tortoise import Tortoise  # noqa: E402

from alttprbot.services import scheduled_jobs  # noqa: E402
from alttprbot.services.scheduler import Scheduler  # noqa: E402
from alttprbot_api.api import sahasrahbotapi  # noqa: E402
from alttprbot_discord import gateways as discord_gateways  # noqa: E402
from alttprbot_discord import notifications as discord_notifications  # noqa: E402
from alttprbot_discord.bot import discordbot, start_bot as start_discord_bot  # noqa: E402
from alttprbot_racetime import gateways as racetime_gateways  # noqa: E402
from alttprbot_racetime.bot import start_racetime  # noqa: E402


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

    # Give services in alttprbot/ the Discord lookups they need.
    discord_gateways.register()
    # ... and the racetime.gg bots (alttprbot.services.bots).
    racetime_gateways.register()
    # Subscribers for the event bridge (alttprbot/events): services and the scheduled
    # jobs publish, these turn events into Discord posts and DMs once the bot is ready.
    discord_notifications.register(discordbot)

    # Periodic jobs run here, not in Discord cogs.
    scheduler = Scheduler()
    scheduled_jobs.register_jobs(
        scheduler,
        discord_ready=lambda: discord_notifications.wait_until_ready(discordbot),
    )
    loop.call_soon(scheduler.start)

    loop.create_task(start_discord_bot())
    start_racetime(loop)
    loop.create_task(sahasrahbotapi.run(host='127.0.0.1', port=5001, use_reloader=False, loop=loop))

    # Event-loop lag, process and bot gauges for Sentry, and the blocked-loop watchdog.
    loop.call_soon(observability_runtime.start)
    if observability.enabled() and observability.setting('SENTRY_LOOP_WATCHDOG', True):
        loop.call_soon(observability_watchdog.start)

    try:
        loop.run_forever()
    finally:
        observability.flush()
