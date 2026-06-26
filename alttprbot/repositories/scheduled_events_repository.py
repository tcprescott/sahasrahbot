"""Data access for the ``scheduled_events`` table (discord guild scheduled events)."""

from typing import List, Optional, Tuple

from alttprbot import models


class ScheduledEventsRepository:
    @staticmethod
    async def list_dead(active_episode_ids: list, event_slug: str) -> List[models.ScheduledEvents]:
        """Scheduled events for this event whose episode is no longer in the schedule."""
        return await models.ScheduledEvents.filter(
            episode_id__not_in=active_episode_ids, event_slug=event_slug
        )

    @staticmethod
    async def get_by_episode(episode_id: int) -> Optional[models.ScheduledEvents]:
        return await models.ScheduledEvents.get_or_none(episode_id=episode_id)

    @staticmethod
    async def upsert_by_episode(
        episode_id: int, *, scheduled_event_id: int, event_slug: str
    ) -> Tuple[models.ScheduledEvents, bool]:
        return await models.ScheduledEvents.update_or_create(
            episode_id=episode_id,
            defaults={"scheduled_event_id": scheduled_event_id, "event_slug": event_slug},
        )

    @staticmethod
    async def create(
        *, scheduled_event_id: int, episode_id: int, event_slug: str
    ) -> models.ScheduledEvents:
        return await models.ScheduledEvents.create(
            scheduled_event_id=scheduled_event_id, episode_id=episode_id, event_slug=event_slug
        )

    @staticmethod
    async def delete_instance(event: models.ScheduledEvents) -> None:
        await event.delete()
