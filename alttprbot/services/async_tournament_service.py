"""Async-tournament service backing the web API.

Owns the pydantic serialization for the API-key ``/api/*`` endpoints (which need
model access) and the race review/reattempt writes, and provides a thin data
facade over the repository for the session-auth endpoints. Authorization
(``is_async_tournament_user``) and leaderboard scoring remain in their existing
shared helpers; this service does not duplicate them.
"""

import datetime
from typing import List, Optional

from tortoise.contrib.pydantic import pydantic_model_creator, pydantic_queryset_creator

from alttprbot import models
from alttprbot.repositories import AsyncTournamentRepository


class AsyncTournamentService:
    def __init__(self) -> None:
        self.repository = AsyncTournamentRepository()

    # --- pydantic-serialized /api/* endpoints ---

    async def tournaments_json(self, active: Optional[bool]) -> str:
        qs = self.repository.tournaments_query(active)
        pydantic = pydantic_queryset_creator(models.AsyncTournament)
        return (await pydantic.from_queryset(qs)).json()

    async def tournament_json(self, tournament_id: int) -> Optional[str]:
        result = await self.repository.get_tournament(tournament_id)
        if result is None:
            return None
        pydantic = pydantic_model_creator(models.AsyncTournament)
        return (await pydantic.from_tortoise_orm(result)).json()

    async def races_json(self, tournament_id: int, filters: dict, page: int, page_size: int) -> str:
        qs = self.repository.races_query(tournament_id, filters, page, page_size)
        pydantic = pydantic_queryset_creator(models.AsyncTournamentRace)
        return (await pydantic.from_queryset(qs)).json()

    async def pools_json(self, tournament_id: int, filters: dict) -> str:
        qs = self.repository.pools_query(tournament_id, filters)
        pydantic = pydantic_queryset_creator(models.AsyncTournamentPermalinkPool)
        return (await pydantic.from_queryset(qs)).json()

    async def permalinks_json(self, tournament_id: int, filters: dict) -> str:
        qs = self.repository.permalinks_query(tournament_id, filters)
        pydantic = pydantic_queryset_creator(models.AsyncTournamentPermalink)
        return (await pydantic.from_queryset(qs)).json()

    # --- permission checks (the discord guild/member resolution stays in presentation) ---

    async def user_has_permission(
        self, tournament: models.AsyncTournament, user: models.Users, roles: list
    ) -> bool:
        return await self.repository.user_has_permission(tournament, user, roles)

    async def role_has_permission(
        self, tournament: models.AsyncTournament, discord_role_ids: list, roles: list
    ) -> bool:
        return await self.repository.role_has_permission(tournament, discord_role_ids, roles)

    # --- data facade (session-auth endpoints shape the JSON themselves) ---

    async def get_tournament(self, tournament_id: int) -> Optional[models.AsyncTournament]:
        return await self.repository.get_tournament(tournament_id)

    async def get_tournament_with_pools(self, tournament_id: int) -> Optional[models.AsyncTournament]:
        return await self.repository.get_tournament_with_pools(tournament_id)

    async def get_permalink(
        self, permalink_id: int, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentPermalink]:
        return await self.repository.get_permalink(permalink_id, tournament)

    async def list_user_races(self, user, tournament) -> List[models.AsyncTournamentRace]:
        return await self.repository.list_user_races(user, tournament)

    async def list_tournament_user_races(self, tournament, user_id) -> List[models.AsyncTournamentRace]:
        return await self.repository.list_tournament_user_races(tournament, user_id)

    async def list_reattempted_races(self, user, tournament) -> List[models.AsyncTournamentRace]:
        return await self.repository.list_reattempted_races(user, tournament)

    async def get_user_race(self, race_id, user, tournament) -> Optional[models.AsyncTournamentRace]:
        return await self.repository.get_user_race(race_id, user, tournament)

    async def get_user_race_with_pool(self, race_id, user, tournament) -> Optional[models.AsyncTournamentRace]:
        return await self.repository.get_user_race_with_pool(race_id, user, tournament)

    async def get_race(self, race_id, tournament) -> Optional[models.AsyncTournamentRace]:
        return await self.repository.get_race(race_id, tournament)

    async def get_race_for_review(self, race_id, tournament) -> Optional[models.AsyncTournamentRace]:
        return await self.repository.get_race_for_review(race_id, tournament)

    async def list_queue_races(self, tournament, request_filter, page, page_size) -> List[models.AsyncTournamentRace]:
        return await self.repository.list_queue_races(tournament, request_filter, page, page_size)

    async def list_permalink_races(self, permalink) -> List[models.AsyncTournamentRace]:
        return await self.repository.list_permalink_races(permalink)

    # --- writes ---

    async def submit_reattempt(self, race: models.AsyncTournamentRace, reason: str) -> None:
        await self.repository.mark_reattempted(race, reason)

    async def claim_for_review(self, race: models.AsyncTournamentRace, reviewer: models.Users) -> None:
        await self.repository.set_reviewer(race, reviewer)

    async def submit_review(
        self,
        race: models.AsyncTournamentRace,
        *,
        review_status: str,
        reviewer_notes: Optional[str],
        reviewer: models.Users,
    ) -> None:
        await self.repository.save_review(
            race,
            review_status=review_status,
            reviewer_notes=reviewer_notes,
            reviewer=reviewer,
            reviewed_at=datetime.datetime.now(),
        )
