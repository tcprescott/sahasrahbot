"""Tournament-results service.

Phase 5 exposes the SRL-id lookup the RaceTime core handler needs; the tournament
decomposition (Phase 7) grows this with the create/update flows.
"""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import TournamentResultsRepository
from alttprbot.services._notify import racetime_gateway


class TournamentResultsService:
    def __init__(self) -> None:
        self.repository = TournamentResultsRepository()

    async def get_by_srl_id(self, srl_id: str) -> Optional[models.TournamentResults]:
        return await self.repository.get_by_srl_id(srl_id)

    async def handle_existing_room_for_episode(self, episode_id, category: str) -> bool:
        """Decide whether a tournament race room may be (re)opened for an episode.

        Returns ``True`` if creation should proceed: either no results row exists, or a
        stale row whose RaceTime room is cancelled (deleted here first). Returns ``False``
        if a non-cancelled room already exists for the episode (refuse to re-open).

        Mirrors the legacy ``tournaments.create_tournament_race_room`` pre-check.
        """
        race = await self.repository.get_by_episode_id(episode_id)
        if race is None:
            return True
        status = await racetime_gateway.get().get_race_status(category, race.srl_id)
        if not status == 'cancelled':
            return False
        await self.repository.delete(race)
        return True
