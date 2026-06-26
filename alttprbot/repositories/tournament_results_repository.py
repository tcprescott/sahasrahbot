"""Data access for the ``tournament_results`` table.

Phase 5 introduces the SRL-id lookup used by the RaceTime core handler; the
tournament decomposition (Phase 7) extends this repository with the
create/update operations currently embedded in the tournament classes.
"""

from typing import Optional

from alttprbot import models


class TournamentResultsRepository:
    @staticmethod
    async def get_by_srl_id(srl_id: str) -> Optional[models.TournamentResults]:
        return await models.TournamentResults.get_or_none(srl_id=srl_id)
