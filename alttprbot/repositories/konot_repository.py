"""Data access for the KONOT race-series tables (game + segment)."""

from typing import Optional

from alttprbot import models


class KONOTRepository:
    @staticmethod
    async def create_game(category_slug: str) -> models.RacetimeKONOTGame:
        return await models.RacetimeKONOTGame.create(category_slug=category_slug)

    @staticmethod
    async def get_game(game_id: int) -> Optional[models.RacetimeKONOTGame]:
        return await models.RacetimeKONOTGame.get_or_none(id=game_id)

    @staticmethod
    async def create_segment(
        *, racetime_room: str, game_id: int, segment_number: int
    ) -> models.RaceTimeKONOTSegment:
        return await models.RaceTimeKONOTSegment.create(
            racetime_room=racetime_room, game_id=game_id, segment_number=segment_number
        )

    @staticmethod
    async def get_segment_by_room(racetime_room: str) -> Optional[models.RaceTimeKONOTSegment]:
        return await models.RaceTimeKONOTSegment.get_or_none(racetime_room=racetime_room)
