"""Data access for the ``async_tournament_live_race`` table."""

from typing import Any, Dict, List, Optional

from alttprbot import models


class AsyncTournamentLiveRaceRepository:
    @staticmethod
    async def get_by_racetime_slug(racetime_slug: str) -> Optional[models.AsyncTournamentLiveRace]:
        return await models.AsyncTournamentLiveRace.get_or_none(racetime_slug=racetime_slug)

    @staticmethod
    async def list_in_progress_slugs(slug_partial: str) -> List[Dict[str, Any]]:
        return await models.AsyncTournamentLiveRace.filter(
            racetime_slug__icontains=slug_partial, status="in_progress"
        ).values("racetime_slug")
