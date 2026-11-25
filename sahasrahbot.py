import asyncio
import signal
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


def shutdown(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel what's still running, then close the loop (what Quart's run() did for us)."""
    tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


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
    # SIGINT/SIGTERM stop the web server gracefully, and then everything else.
    # (Quart's app.run() would block here until shutdown and close the loop itself,
    # so nothing below it ever ran: use run_task and own the loop instead.)
    stop = asyncio.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    api_task = loop.create_task(sahasrahbotapi.run_task(host='127.0.0.1', port=5001, shutdown_trigger=stop.wait))

    # Event-loop lag, process and bot gauges for Sentry, and the blocked-loop watchdog.
    loop.call_soon(observability_runtime.start)
    if observability.enabled() and observability.setting('SENTRY_LOOP_WATCHDOG', True):
        loop.call_soon(observability_watchdog.start)

    try:
        # Ends after a signal, or raises if the web server dies (e.g. port in use).
        loop.run_until_complete(api_task)
    finally:
        try:
            shutdown(loop)
        finally:
            observability.flush()
