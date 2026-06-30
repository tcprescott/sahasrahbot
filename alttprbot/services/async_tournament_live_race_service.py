"""Async-tournament live-race service."""

from typing import Any, Dict, List, Optional

from alttprbot import models
from alttprbot.repositories import AsyncTournamentLiveRaceRepository


class AsyncTournamentLiveRaceService:
    def __init__(self) -> None:
        self.repository = AsyncTournamentLiveRaceRepository()

    async def get_by_racetime_slug(self, racetime_slug: str) -> Optional[models.AsyncTournamentLiveRace]:
        return await self.repository.get_by_racetime_slug(racetime_slug)

    async def list_in_progress_slugs(self, slug_partial: str) -> List[Dict[str, Any]]:
        return await self.repository.list_in_progress_slugs(slug_partial)
