"""Tournament scheduling service: discord scheduled-event records + preset history.

Owns the data side of syncing SpeedGaming episodes to discord guild scheduled
events. Discord ScheduledEvent creation/editing/deletion stays in the cog.
"""

from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import ScheduledEventsRepository, TournamentPresetHistoryRepository


class TournamentSchedulingService:
    def __init__(self) -> None:
        self.scheduled_events = ScheduledEventsRepository()
        self.preset_history = TournamentPresetHistoryRepository()

    async def delete_preset_history(self, episode_id: int, event_slug: str) -> int:
        return await self.preset_history.delete_for_episode(episode_id, event_slug)

    async def list_dead_scheduled_events(
        self, active_episode_ids: list, event_slug: str
    ) -> List[models.ScheduledEvents]:
        return await self.scheduled_events.list_dead(active_episode_ids, event_slug)

    async def get_scheduled_event(self, episode_id: int) -> Optional[models.ScheduledEvents]:
        return await self.scheduled_events.get_by_episode(episode_id)

    async def upsert_scheduled_event(
        self, episode_id: int, *, scheduled_event_id: int, event_slug: str
    ) -> None:
        await self.scheduled_events.upsert_by_episode(
            episode_id, scheduled_event_id=scheduled_event_id, event_slug=event_slug
        )

    async def create_scheduled_event(
        self, *, scheduled_event_id: int, episode_id: int, event_slug: str
    ) -> None:
        await self.scheduled_events.create(
            scheduled_event_id=scheduled_event_id, episode_id=episode_id, event_slug=event_slug
        )

    async def delete_scheduled_event(self, event: models.ScheduledEvents) -> None:
        await self.scheduled_events.delete_instance(event)
