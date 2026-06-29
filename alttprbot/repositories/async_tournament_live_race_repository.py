"""Data access for the ``async_tournament_live_race`` table."""

from datetime import datetime
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

    @staticmethod
    async def get_by_episode_id(episode_id: int) -> Optional[models.AsyncTournamentLiveRace]:
        return await models.AsyncTournamentLiveRace.get_or_none(episode_id=episode_id)

    @staticmethod
    async def get_by_episode_id_with_relations(
        episode_id: int,
    ) -> Optional[models.AsyncTournamentLiveRace]:
        """Fetch the live race for an episode with the relations the qualifier roll needs."""
        live_race = await models.AsyncTournamentLiveRace.get_or_none(episode_id=episode_id)
        if live_race is not None:
            await live_race.fetch_related("pool", "permalink", "tournament")
        return live_race

    @staticmethod
    async def set_permalink_and_slug(
        live_race: models.AsyncTournamentLiveRace,
        permalink: models.AsyncTournamentPermalink,
        racetime_slug: str,
    ) -> None:
        live_race.permalink = permalink
        live_race.racetime_slug = racetime_slug
        await live_race.save()

    @staticmethod
    async def process_race_start(
        live_race: models.AsyncTournamentLiveRace,
        entrant_rtgg_ids: List[str],
        start_time: datetime,
    ) -> List[str]:
        """Flip pending entrants to in-progress, prune no-shows, mark the live race started.

        Mirrors the legacy ``process_async_tournament_start``: actual entrants (pending and
        present in the room) become ``in_progress`` with ``start_time``; remaining pending
        rows (entrants who never joined) are deleted; the live race is marked in-progress.
        Returns the in-progress runners' display names.

        The promote is done as select-ids-then-update-by-id rather than a single
        ``UPDATE ... JOIN`` (the legacy filtered-on-a-relation update) so the query is
        portable to SQLite; the set of rows touched is identical.
        """
        to_promote = await models.AsyncTournamentRace.filter(
            live_race=live_race,
            status="pending",
            user__rtgg_id__in=entrant_rtgg_ids,
        ).values_list("id", flat=True)
        if to_promote:
            await models.AsyncTournamentRace.filter(id__in=to_promote).update(
                status="in_progress", start_time=start_time
            )

        await models.AsyncTournamentRace.filter(live_race=live_race, status="pending").delete()

        live_race.status = "in_progress"
        await live_race.save()

        in_progress = await models.AsyncTournamentRace.filter(
            live_race=live_race, status="in_progress"
        ).prefetch_related("user")
        return [entrant.user.display_name for entrant in in_progress]
