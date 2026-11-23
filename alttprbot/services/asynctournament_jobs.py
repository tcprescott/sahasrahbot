"""Scheduled async tournament jobs: run timeouts and score recalculation.

These used to be ``discord.ext.tasks`` loops in ``alttprbot_discord/cogs/asynctournament.py``.

A timeout is only applied after the runner has been told in their race thread, and a
run whose thread can't be reached is left alone, so the job needs an answer from
Discord rather than a fire-and-forget event. ``sahasrahbot.py`` registers that
notifier (``set_timeout_notifier``) through ``alttprbot_discord/gateways.py``.
"""
import logging
from typing import Awaitable, Callable, Optional

from alttprbot import models
from alttprbot.services import asynctournament as service
from alttprbot.util import asynctournament

logger = logging.getLogger(__name__)

# Tells the runner about a timeout action. Returns True if they were told.
TimeoutNotifier = Callable[[service.TimeoutAction], Awaitable[bool]]

_timeout_notifier: Optional[TimeoutNotifier] = None


def set_timeout_notifier(notifier: Optional[TimeoutNotifier]) -> None:
    global _timeout_notifier
    _timeout_notifier = notifier


async def _handle(actions: list[service.TimeoutAction]) -> None:
    if not actions:
        return
    if _timeout_notifier is None:
        logger.warning("No timeout notifier registered; leaving %d async race timeouts for later.", len(actions))
        return
    for action in actions:
        try:
            told = await _timeout_notifier(action)
        except Exception:
            logger.exception("Unable to notify the runner of async race %s.", action.race.id)
            continue
        if told and action.forfeits:
            await service.apply_timeout_forfeit(action)


async def timeout_pending_races() -> None:
    """Warn runners who haven't started, and forfeit them after the grace period."""
    await _handle(await service.find_pending_timeouts())


async def timeout_in_progress_races() -> None:
    """Forfeit runs that have been in progress for more than 12 hours."""
    await _handle(await service.find_in_progress_timeouts())


async def calculate_scores() -> None:
    tournaments = await models.AsyncTournament.filter(active=True)
    for tournament in tournaments:
        logger.info("Calculating scores for tournament %s", tournament.id)
        try:
            await asynctournament.calculate_async_tournament(tournament)
        except Exception:
            logger.exception("Exception in score_calculation_task for tournament %s", tournament.id)
        logger.info("Finished calculating scores for tournament %s", tournament.id)
