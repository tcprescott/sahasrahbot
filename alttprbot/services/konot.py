"""KONOT ("knock out") race series: each finished race eliminates its last finisher
and opens the next segment's room.

This is the only module that reads or writes ``models.RacetimeKONOTGame`` and
``models.RaceTimeKONOTSegment``. Room creation and invites stay in
``alttprbot_racetime/misc/konot.py``.
"""

from typing import Tuple

from alttprbot import models


async def start_game(category: str, room_name: str) -> Tuple[models.RacetimeKONOTGame, models.RaceTimeKONOTSegment]:
    """Create a new series with this room as segment 1."""
    game = await models.RacetimeKONOTGame.create(category_slug=category)
    segment = await add_segment(game.id, room_name, 1)
    return game, segment


async def add_segment(game_id: int, room_name: str, segment_number: int) -> models.RaceTimeKONOTSegment:
    return await models.RaceTimeKONOTSegment.create(
        racetime_room=room_name,
        game_id=game_id,
        segment_number=segment_number
    )


async def find_by_room(room_name: str) -> Tuple[models.RacetimeKONOTGame, models.RaceTimeKONOTSegment]:
    """The series and segment played in this room.

    Raises ``tortoise.exceptions.DoesNotExist`` when the room is not part of one.
    """
    segment = await models.RaceTimeKONOTSegment.get(racetime_room=room_name)
    game = await models.RacetimeKONOTGame.get(id=segment.game_id)
    return game, segment
