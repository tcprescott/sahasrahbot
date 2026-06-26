"""Tournament-results service.

Phase 5 exposes the SRL-id lookup the RaceTime core handler needs; the tournament
decomposition (Phase 7) grows this with the create/update flows.
"""

from typing import Optional

from alttprbot import models
from alttprbot.repositories import TournamentResultsRepository


class TournamentResultsService:
    def __init__(self) -> None:
        self.repository = TournamentResultsRepository()

    async def get_by_srl_id(self, srl_id: str) -> Optional[models.TournamentResults]:
        return await self.repository.get_by_srl_id(srl_id)
