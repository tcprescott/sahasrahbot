import logging
import sys

import asyncio

from alttprbot_racetime.config import RACETIME_CATEGORIES

logger = logging.getLogger()
logger_handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)

logger_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s'
))
logger.addHandler(logger_handler)


def start_racetime():
    """
    Start all Racetime bots in the given event loop.
    """
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


racetime_bots = {}
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
