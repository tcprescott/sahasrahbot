"""Data access for the ``tournament_results`` table.

Phase 5 introduces the SRL-id lookup used by the RaceTime core handler; the
tournament decomposition (Phase 7) extends this repository with the
create/update operations currently embedded in the tournament classes.
"""

from typing import Optional, Tuple

from alttprbot import models


class TournamentResultsRepository:
    @staticmethod
    async def get_by_srl_id(srl_id: str) -> Optional[models.TournamentResults]:
        return await models.TournamentResults.get_or_none(srl_id=srl_id)

    @staticmethod
    async def upsert_by_srl_id(
        srl_id: str, defaults: dict
    ) -> Tuple[models.TournamentResults, bool]:
        """Update-or-create a result row keyed on ``srl_id`` with ``defaults``.

        Mirrors ``TournamentResults.update_or_create(srl_id=..., defaults=...)`` so
        callers keep their existing field semantics while the ORM call is owned here.
        """
        return await models.TournamentResults.update_or_create(srl_id=srl_id, defaults=defaults)
