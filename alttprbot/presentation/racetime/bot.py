import logging
import sys

import asyncio

from alttprbot.presentation.racetime.config import RACETIME_CATEGORIES

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)

logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)


# The per-category bots are built at startup (build_racetime_bots), NOT at import: the
# credential validation below would otherwise require RaceTime secrets just to import this
# module, breaking test collection (and any non-racetime consumer) in environments without
# them. The dict is populated in place, so the gateway registered at import still sees the
# bots once startup runs.
racetime_bots = {}


def build_racetime_bots():
    """Build the per-category RaceTime bots into ``racetime_bots`` (idempotent).

    Validates credentials here (fail-fast at startup) rather than at import time.
    """
    if racetime_bots:
        return racetime_bots
    for slug, category in RACETIME_CATEGORIES.items():
        if not category.client_id:
            raise ValueError(f"Racetime category {slug} has no client id")
        if not category.client_secret:
            raise ValueError(f"Racetime category {slug} has no client secret")
        racetime_bots[slug] = category.bot_class(
            category_slug=slug,
            client_id=category.client_id,
            client_secret=category.client_secret,
            logger=logger,
            handler_class=category.handler_class
        )
    return racetime_bots


def start_racetime():
    """
    Start all Racetime bots in the given event loop.
    """
    build_racetime_bots()
    tasks = []
    for bot in racetime_bots.values():
        task = asyncio.create_task(bot.start())
        tasks.append(task)
    return tasks


async def stop_racetime():
    """
    Stop all Racetime bots gracefully.
    """
    await asyncio.gather(*(bot.stop() for bot in racetime_bots.values()), return_exceptions=True)


# Register the concrete RaceTime gateway inward so the service tier can reach RaceTime
# without importing the bot singletons. Resolution is lazy (per-call handler lookup), and the
# impl holds the racetime_bots dict reference — populated in place by build_racetime_bots().
from alttprbot.presentation.racetime import gateway_impl as _gateway_impl  # noqa: E402

_gateway_impl.register(racetime_bots)
