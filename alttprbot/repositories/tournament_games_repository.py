"""Data access for the ``tournament_games`` table.

Introduced in the Phase 7 tournament data-layer foundation. The tournament base
class routes its TournamentGames access here; subclasses migrate one per PR during
the orchestrator/presenter decomposition.
"""

from typing import Optional, Tuple

from alttprbot import models


class TournamentGamesRepository:
    @staticmethod
    async def get_by_episode_id(episode_id) -> Optional[models.TournamentGames]:
        return await models.TournamentGames.get_or_none(episode_id=episode_id)

    @staticmethod
    async def upsert_by_episode_id(
        episode_id, defaults: dict
    ) -> Tuple[models.TournamentGames, bool]:
        """Update-or-create a game row keyed on ``episode_id`` with ``defaults``."""
        return await models.TournamentGames.update_or_create(
            episode_id=episode_id, defaults=defaults
        )
