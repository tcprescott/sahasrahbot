"""Data access for the async-tournament tables.

Backs the async-tournament web API: tournament/race/pool/permalink reads (some
returned as querysets for pydantic serialization in the service) plus the race
review/reattempt writes.
"""

from datetime import datetime
from typing import List, Optional

from tortoise.functions import Count

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
    async def is_user_whitelisted(
        tournament: models.AsyncTournament, discord_user_id: int
    ) -> bool:
        return await tournament.whitelist.filter(user__discord_user_id=discord_user_id).exists()

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

    # --- live-qualifier writes (used by the alttpr_quals roll) ---

    @staticmethod
    async def create_live_permalink(
        url: str, pool: models.AsyncTournamentPermalinkPool, notes: str
    ) -> models.AsyncTournamentPermalink:
        return await models.AsyncTournamentPermalink.create(
            url=url, pool=pool, notes=notes, live_race=True
        )

    @staticmethod
    async def count_completed_pool_races(
        tournament: models.AsyncTournament, user: models.Users, pool: models.AsyncTournamentPermalinkPool
    ) -> int:
        """Non-reattempted races this user has already run from this pool (run-limit check)."""
        return await models.AsyncTournamentRace.filter(
            tournament=tournament, user=user, permalink__pool=pool, reattempted=False
        ).count()

    @staticmethod
    async def user_has_active_race(
        tournament: models.AsyncTournament, user: models.Users
    ) -> bool:
        return await models.AsyncTournamentRace.filter(
            tournament=tournament, user=user, status__in=["pending", "in_progress"]
        ).exists()

    @staticmethod
    async def create_pending_live_entry(
        tournament: models.AsyncTournament,
        permalink: models.AsyncTournamentPermalink,
        user: models.Users,
        live_race: models.AsyncTournamentLiveRace,
    ) -> models.AsyncTournamentRace:
        return await models.AsyncTournamentRace.create(
            tournament=tournament,
            permalink=permalink,
            user=user,
            thread_id=None,
            status="pending",
            live_race=live_race,
        )

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

    # --- discord-cog reads ---

    @staticmethod
    async def get_by_channel_id(channel_id: int) -> Optional[models.AsyncTournament]:
        return await models.AsyncTournament.get_or_none(channel_id=channel_id)

    @staticmethod
    async def list_active() -> List[models.AsyncTournament]:
        return await models.AsyncTournament.filter(active=True)

    @staticmethod
    async def get_pool_by_name(
        tournament: models.AsyncTournament, name: str
    ) -> Optional[models.AsyncTournamentPermalinkPool]:
        return await models.AsyncTournamentPermalinkPool.get_or_none(tournament=tournament, name=name)

    @staticmethod
    async def list_user_races_by_discord_id(
        tournament: models.AsyncTournament, discord_user_id: int
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            user__discord_user_id=discord_user_id, tournament=tournament
        ).prefetch_related("permalink__pool")

    @staticmethod
    async def list_active_races_for_user(
        tournament: models.AsyncTournament, discord_user_id: int, statuses: list
    ) -> List[models.AsyncTournamentRace]:
        return await tournament.races.filter(
            user__discord_user_id=discord_user_id, status__in=statuses
        )

    @staticmethod
    async def get_race_by_thread_id(thread_id: int) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(thread_id=thread_id)

    @staticmethod
    async def get_race_by_thread_id_with_user(
        thread_id: int,
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(
            thread_id=thread_id
        ).prefetch_related("user")

    @staticmethod
    async def get_race_by_thread_id_with_user_and_tournament(
        thread_id: int,
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(
            thread_id=thread_id
        ).prefetch_related("user", "tournament")

    @staticmethod
    async def get_race_by_thread_id_with_tournament(
        thread_id: int,
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(
            thread_id=thread_id
        ).prefetch_related("tournament")

    @staticmethod
    async def get_race_by_live_race_and_user(
        live_race: models.AsyncTournamentLiveRace, user: models.Users
    ) -> Optional[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.get_or_none(live_race=live_race, user=user)

    @staticmethod
    async def list_pending_races() -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            status="pending", thread_id__isnull=False
        ).prefetch_related("user")

    @staticmethod
    async def list_in_progress_races() -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            status="in_progress", thread_id__isnull=False
        ).prefetch_related("user")

    @staticmethod
    async def count_in_progress_races_for_live_race(
        live_race: models.AsyncTournamentLiveRace,
    ) -> int:
        return await models.AsyncTournamentRace.filter(
            live_race=live_race, status="in_progress"
        ).count()

    # --- discord-cog creates ---

    @staticmethod
    async def create_tournament(
        *,
        name: str,
        report_channel_id: Optional[int],
        active: bool,
        guild_id: int,
        channel_id: int,
        owner_id: int,
    ) -> models.AsyncTournament:
        return await models.AsyncTournament.create(
            name=name,
            report_channel_id=report_channel_id,
            active=active,
            guild_id=guild_id,
            channel_id=channel_id,
            owner_id=owner_id,
        )

    @staticmethod
    async def create_pool(
        *, tournament: models.AsyncTournament, name: str, preset: str
    ) -> models.AsyncTournamentPermalinkPool:
        return await models.AsyncTournamentPermalinkPool.create(
            tournament=tournament, name=name, preset=preset
        )

    @staticmethod
    async def create_permalink(
        *,
        pool: models.AsyncTournamentPermalinkPool,
        url: str,
        notes: Optional[str],
        live_race: bool = False,
    ) -> models.AsyncTournamentPermalink:
        return await models.AsyncTournamentPermalink.create(
            pool=pool, url=url, notes=notes, live_race=live_race
        )

    @staticmethod
    async def create_race(
        *,
        tournament: models.AsyncTournament,
        user: models.Users,
        permalink: models.AsyncTournamentPermalink,
        thread_id: int,
        thread_open_time: datetime,
    ) -> models.AsyncTournamentRace:
        return await models.AsyncTournamentRace.create(
            tournament=tournament,
            thread_id=thread_id,
            user=user,
            thread_open_time=thread_open_time,
            permalink=permalink,
        )

    # --- discord-cog writes (the cog builds the new state; persistence is owned here) ---

    @staticmethod
    async def save_race(race: models.AsyncTournamentRace) -> None:
        await race.save()

    @staticmethod
    async def save_race_fields(race: models.AsyncTournamentRace, fields: list) -> None:
        await race.save(update_fields=fields)

    @staticmethod
    async def save_live_race_fields(
        live_race: models.AsyncTournamentLiveRace, fields: list
    ) -> None:
        await live_race.save(update_fields=fields)

    @staticmethod
    async def save_tournament(tournament: models.AsyncTournament) -> None:
        await tournament.save()

    # --- scoring / leaderboard / eligibility data access ---

    @staticmethod
    async def fetch_pools_with_permalinks(tournament: models.AsyncTournament) -> None:
        await tournament.fetch_related("permalink_pools", "permalink_pools__permalinks")

    @staticmethod
    async def fetch_pools(tournament: models.AsyncTournament) -> None:
        await tournament.fetch_related("permalink_pools")

    @staticmethod
    async def list_races_for_par(
        permalink: models.AsyncTournamentPermalink, only_approved: bool = False
    ) -> List[models.AsyncTournamentRace]:
        """Races used to compute a permalink's par/scores: completed, non-reattempted."""
        query_filter = {
            "permalink": permalink,
            "status__in": ["finished", "forfeit", "disqualified"],
            "reattempted": False,
        }
        if only_approved:
            query_filter["review_status"] = "approved"
        return await models.AsyncTournamentRace.filter(**query_filter).order_by()

    @staticmethod
    async def save_permalink_par(
        permalink: models.AsyncTournamentPermalink, par_time: float, par_updated_at: datetime
    ) -> None:
        permalink.par_time = par_time
        permalink.par_updated_at = par_updated_at
        await permalink.save()

    @staticmethod
    async def save_race_score(
        race: models.AsyncTournamentRace, score: float, score_updated_at: datetime
    ) -> None:
        race.score = score
        race.score_updated_at = score_updated_at
        await race.save(update_fields=["score", "score_updated_at"])

    @staticmethod
    async def fetch_pool_tournament_and_permalinks(
        pool: models.AsyncTournamentPermalinkPool,
    ) -> None:
        await pool.fetch_related("tournament", "permalinks")

    @staticmethod
    async def permalink_play_counts(pool: models.AsyncTournamentPermalinkPool) -> List[dict]:
        """Per-permalink play counts for the pool (across all users)."""
        return await models.AsyncTournamentRace.filter(
            tournament=pool.tournament, permalink__pool=pool
        ).annotate(count=Count("permalink_id")).group_by("permalink_id").values(
            "permalink_id", "count"
        )

    @staticmethod
    async def list_player_pool_history(
        pool: models.AsyncTournamentPermalinkPool, user: models.Users
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            user=user, tournament=pool.tournament, permalink__pool=pool
        ).prefetch_related("permalink")

    @staticmethod
    async def list_available_permalinks(
        pool: models.AsyncTournamentPermalinkPool,
    ) -> List[models.AsyncTournamentPermalink]:
        return await pool.permalinks.filter(live_race=False)

    @staticmethod
    async def get_permalink_by_id(
        permalink_id: int,
    ) -> models.AsyncTournamentPermalink:
        return await models.AsyncTournamentPermalink.get(id=permalink_id)

    @staticmethod
    async def list_participant_user_ids(tournament: models.AsyncTournament) -> List[int]:
        rows = await tournament.races.all().distinct().values("user_id")
        return [row["user_id"] for row in rows]

    @staticmethod
    async def list_user_pool_scored_races(
        user_id: int,
        tournament: models.AsyncTournament,
        pool: models.AsyncTournamentPermalinkPool,
    ) -> List[models.AsyncTournamentRace]:
        return await models.AsyncTournamentRace.filter(
            user_id=user_id,
            tournament=tournament,
            permalink__pool=pool,
            status__in=["finished", "forfeit", "disqualified"],
            reattempted=False,
        )

    @staticmethod
    async def get_user(user_id: int) -> models.Users:
        return await models.Users.get(id=user_id)

    # --- test-data population (DEBUG only; the service enforces the guard) ---

    @staticmethod
    async def create_test_user(discord_user_id: int, display_name: str) -> models.Users:
        return await models.Users.create(
            discord_user_id=discord_user_id, display_name=display_name, test_user=True
        )

    @staticmethod
    async def create_finished_test_race(
        *,
        tournament: models.AsyncTournament,
        user: models.Users,
        permalink: models.AsyncTournamentPermalink,
        thread_id: int,
        thread_open_time: datetime,
        start_time: datetime,
        end_time: datetime,
    ) -> models.AsyncTournamentRace:
        return await models.AsyncTournamentRace.create(
            tournament=tournament,
            thread_id=thread_id,
            user=user,
            thread_open_time=thread_open_time,
            permalink=permalink,
            status="finished",
            start_time=start_time,
            end_time=end_time,
        )
