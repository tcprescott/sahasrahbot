"""Tournament-games service.

Guards the public ``/api/tournament/games`` search: only known column names may
become filter terms, closing the mass-assignment hole where arbitrary query-string
keys were forwarded straight into ``TournamentGames.filter(**request.args)``.
"""

from typing import Any, Dict, List

from alttprbot.repositories import TournamentGamesRepository

# Columns a caller may filter on. Unknown keys are dropped rather than forwarded
# to the ORM (which would either leak query surface or raise on bad fields).
_FILTERABLE_FIELDS = frozenset(
    {
        "episode_id",
        "event",
        "game_number",
        "preset",
        "submitted",
    }
)


class TournamentGamesService:
    def __init__(self) -> None:
        self.repository = TournamentGamesRepository()

    async def search(self, raw_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        filters = {key: value for key, value in raw_filters.items() if key in _FILTERABLE_FIELDS}
        return await self.repository.search(filters)
