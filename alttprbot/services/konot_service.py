"""KONOT race-series service (game + segment persistence)."""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import KONOTRepository


class KONOTService:
    def __init__(self) -> None:
        self.repository = KONOTRepository()

    async def create_game(self, category_slug: str) -> models.RacetimeKONOTGame:
        return await self.repository.create_game(category_slug)

    async def get_game(self, game_id: int) -> Optional[models.RacetimeKONOTGame]:
        return await self.repository.get_game(game_id)

    async def create_segment(
        self, *, racetime_room: str, game_id: int, segment_number: int
    ) -> models.RaceTimeKONOTSegment:
        return await self.repository.create_segment(
            racetime_room=racetime_room, game_id=game_id, segment_number=segment_number
        )

    async def get_segment_by_room(self, racetime_room: str) -> Optional[models.RaceTimeKONOTSegment]:
        return await self.repository.get_segment_by_room(racetime_room)
