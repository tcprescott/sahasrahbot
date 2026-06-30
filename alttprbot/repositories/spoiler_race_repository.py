"""Data access for the ``spoiler_races`` table."""

from datetime import datetime
from typing import Optional, Tuple

from alttprbot import models


class SpoilerRaceRepository:
    @staticmethod
    async def get_by_srl_id(srl_id: str) -> Optional[models.SpoilerRaces]:
        return await models.SpoilerRaces.get_or_none(srl_id=srl_id)

    @staticmethod
    async def upsert(
        *, srl_id: str, spoiler_url: str, studytime: int
    ) -> Tuple[models.SpoilerRaces, bool]:
        return await models.SpoilerRaces.update_or_create(
            srl_id=srl_id,
            defaults={"spoiler_url": spoiler_url, "studytime": studytime},
        )

    @staticmethod
    async def mark_started(spoiler_race: models.SpoilerRaces, started: datetime) -> None:
        spoiler_race.started = started
        await spoiler_race.save(update_fields=["started"])

    @staticmethod
    async def delete_instance(spoiler_race: models.SpoilerRaces) -> None:
        await spoiler_race.delete()
