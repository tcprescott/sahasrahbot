"""Spoiler races: a race room whose spoiler log is posted when the race starts,
followed by a study-time countdown.

This is the only module that reads or writes ``models.SpoilerRaces``. Rows are keyed
by the racetime.gg room name (``srl_id``, e.g. ``alttpr/cool-room-1234``). The race
handlers keep the chat messages and the countdown; this module only stores the row.
"""

from datetime import datetime
from typing import Optional

from alttprbot import models


async def get(room_name: str) -> Optional[models.SpoilerRaces]:
    """The spoiler race for this room, or None."""
    return await models.SpoilerRaces.get_or_none(srl_id=room_name)


async def schedule(room_name: str, spoiler_url: str, studytime: int) -> models.SpoilerRaces:
    """Create the room's spoiler race, or replace its URL and study time."""
    spoiler_race, _ = await models.SpoilerRaces.update_or_create(
        srl_id=room_name,
        defaults={
            'spoiler_url': spoiler_url,
            'studytime': studytime,
        }
    )
    return spoiler_race


async def mark_started(spoiler_race: models.SpoilerRaces) -> None:
    """Record that the spoiler log was sent (naive UTC, as before)."""
    spoiler_race.started = datetime.utcnow()
    await spoiler_race.save(update_fields=['started'])


async def delete(spoiler_race: models.SpoilerRaces) -> None:
    await spoiler_race.delete()
