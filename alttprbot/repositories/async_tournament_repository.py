"""Data access for the async-tournament tables.

Backs the async-tournament web API: tournament/race/pool/permalink reads (some
returned as querysets for pydantic serialization in the service) plus the race
review/reattempt writes.
"""

from datetime import datetime
from typing import List, Optional

from alttprbot import models


class AsyncTournamentRepository:
    # --- single fetches ---

    @staticmethod
    async def get_tournament(tournament_id: int) -> Optional[models.AsyncTournament]:
        return await models.AsyncTournament.get_or_none(id=tournament_id)

    @staticmethod
    async def get_tournament_with_pools(tournament_id: int) -> Optional[models.AsyncTournament]:
        tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
        if tournament is not None:
            await tournament.fetch_related("permalink_pools", "permalink_pools__permalinks")
        return tournament

    # --- permission checks ---

    @staticmethod
    async def user_has_permission(
        tournament: models.AsyncTournament, user: models.Users, roles: list
    ) -> bool:
        return await tournament.permissions.filter(user=user, role__in=roles).exists()

    @staticmethod
    async def role_has_permission(
        tournament: models.AsyncTournament, discord_role_ids: list, roles: list
    ) -> bool:
        return await tournament.permissions.filter(
            discord_role_id__in=discord_role_ids, role__in=roles
        ).exists()

    @staticmethod
    async def get_permalink(
        permalink_id: int, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentPermalink]:
        permalink = await models.AsyncTournamentPermalink.get_or_none(
            id=permalink_id, pool__tournament=tournament
        )
        if permalink is not None:
            await permalink.fetch_related("pool")
        return permalink

    # --- querysets for the pydantic /api/* endpoints (serialized in the service) ---

    @staticmethod
    def tournaments_query(active: Optional[bool]):
        filter_args = {} if active is None else {"active": active}
        return models.AsyncTournament.filter(**filter_args)

    @staticmethod
    def races_query(tournament_id: int, filters: dict, page: int, page_size: int):
        return (
            models.AsyncTournamentRace.filter(tournament_id=tournament_id, **filters)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

    @staticmethod
    def pools_query(tournament_id: int, filters: dict):
        return models.AsyncTournamentPermalinkPool.filter(tournament_id=tournament_id, **filters)

    @staticmethod
    def permalinks_query(tournament_id: int, filters: dict):
        return models.AsyncTournamentPermalink.filter(pool__tournament_id=tournament_id, **filters)

    # --- race fetches ---

    @staticmethod
    async def list_user_races(
        user: models.Users, tournament: models.AsyncTournament
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            user=user, tournament=tournament
        ).order_by("-created").prefetch_related("permalink", "permalink__pool")

    @staticmethod
    async def list_tournament_user_races(
        tournament: models.AsyncTournament, user_id: int
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            tournament=tournament, user_id=user_id
        ).order_by("-created").prefetch_related("permalink", "permalink__pool")

    @staticmethod
    async def list_reattempted_races(
        user: models.Users, tournament: models.AsyncTournament
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            user=user, tournament=tournament, reattempted=True
        )

    @staticmethod
    async def get_user_race(
        race_id: int, user: models.Users, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(
            id=race_id, user=user, tournament=tournament
        )

    @staticmethod
    async def get_user_race_with_pool(
        race_id: int, user: models.Users, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentRace]:
        race = await models.AsyncTournamentRace.get_or_none(
            id=race_id, user=user, tournament=tournament
        )
        if race is not None:
            await race.fetch_related("permalink", "permalink__pool")
        return race

    @staticmethod
    async def get_race(
        race_id: int, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)

    @staticmethod
    async def get_race_for_review(
        race_id: int, tournament: models.AsyncTournament
    ) -> Optional[models.AsyncTournamentRace]:
        race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
        if race is not None:
            await race.fetch_related(
                "user", "reviewed_by", "permalink", "permalink__pool", "live_race"
            )
        return race

    @staticmethod
    async def list_queue_races(
        tournament: models.AsyncTournament, request_filter: dict, page: int, page_size: int
    ) -> List[models.AsyncTournamentRace]:
        return await tournament.races.filter(
            reattempted=False, **request_filter
        ).offset((page - 1) * page_size).limit(page_size).prefetch_related(
            "user", "reviewed_by", "permalink", "permalink__pool"
        )

    @staticmethod
    async def list_permalink_races(
        permalink: models.AsyncTournamentPermalink,
    ) -> List[models.AsyncTournamentRace]:
        return await permalink.races.filter(
            status__in=["finished", "forfeit"], reattempted=False
        ).order_by("-score").prefetch_related("live_race")

    # --- writes ---

    @staticmethod
    async def mark_reattempted(race: models.AsyncTournamentRace, reason: str) -> None:
        race.reattempted = True
        race.reattempt_reason = reason
        await race.save()

    @staticmethod
    async def set_reviewer(race: models.AsyncTournamentRace, reviewer: models.Users) -> None:
        race.reviewed_by = reviewer
        await race.save()

    @staticmethod
    async def save_review(
        race: models.AsyncTournamentRace,
        *,
        review_status: str,
        reviewer_notes: Optional[str],
        reviewer: models.Users,
        reviewed_at: datetime,
    ) -> None:
        race.review_status = review_status
        race.reviewer_notes = reviewer_notes
        race.reviewed_at = reviewed_at
        race.reviewed_by = reviewer
        await race.save()
