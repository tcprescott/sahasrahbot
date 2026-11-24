"""Which Discord guild scheduled event mirrors which SpeedGaming episode.

This is the only module that reads or writes ``models.ScheduledEvents``. The Discord
side (``alttprbot_discord/notifications.py``) creates, edits and deletes the guild
events; this module only remembers their ids.
"""

from typing import Iterable, List, Optional

from tortoise.transactions import in_transaction

from alttprbot import models


async def stale(event_slug: str, live_episode_ids: Iterable) -> List[models.ScheduledEvents]:
    """The event's remembered guild events whose episode is no longer on the schedule
    (use ``.scheduled_event_id`` and ``.episode_id``)."""
    return await models.ScheduledEvents.filter(episode_id__not_in=list(live_episode_ids), event_slug=event_slug)


async def for_episode(episode_id: int) -> Optional[models.ScheduledEvents]:
    return await models.ScheduledEvents.get_or_none(episode_id=episode_id)


async def remember(episode_id: int, scheduled_event_id: int, event_slug: str) -> None:
    """Record (or replace) the guild event that mirrors this episode.

    ``scheduled_event_id`` is the primary key, which ``update_or_create`` can't change,
    so a replaced guild event's row is deleted and created again.
    """
    async with in_transaction():
        await models.ScheduledEvents.filter(episode_id=episode_id).exclude(
            scheduled_event_id=scheduled_event_id).delete()
        await models.ScheduledEvents.update_or_create(
            scheduled_event_id=scheduled_event_id, defaults={'episode_id': episode_id, 'event_slug': event_slug})


async def forget(scheduled_event_id: int) -> None:
    await models.ScheduledEvents.filter(scheduled_event_id=scheduled_event_id).delete()
