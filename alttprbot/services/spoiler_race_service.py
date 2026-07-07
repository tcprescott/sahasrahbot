"""Spoiler-race service for the RaceTime surface.

Owns the spoiler-race record lifecycle (lookup, schedule, mark started, delete).
The countdown/timer orchestration stays in the RaceTime handler (presentation).
"""

from datetime import datetime, timezone
from typing import Optional

from alttprbot import models
from alttprbot.repositories import SpoilerRaceRepository


class SpoilerRaceService:
    def __init__(self) -> None:
        self.repository = SpoilerRaceRepository()

    async def get_for_room(self, srl_id: str) -> Optional[models.SpoilerRaces]:
        return await self.repository.get_by_srl_id(srl_id)

    async def schedule(self, *, srl_id: str, spoiler_url: str, studytime: int) -> models.SpoilerRaces:
        spoiler_race, _ = await self.repository.upsert(
            srl_id=srl_id, spoiler_url=spoiler_url, studytime=studytime
        )
        return spoiler_race

    async def mark_started(self, spoiler_race: models.SpoilerRaces) -> None:
        await self.repository.mark_started(spoiler_race, datetime.now(timezone.utc).replace(tzinfo=None))

    async def delete(self, spoiler_race: models.SpoilerRaces) -> None:
        await self.repository.delete_instance(spoiler_race)
