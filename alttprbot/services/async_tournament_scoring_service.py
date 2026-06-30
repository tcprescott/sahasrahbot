"""Async-tournament scoring, leaderboard, eligibility, and test-data service.

Houses the algorithmic side of async tournaments that used to live in
``alttprbot.util.asynctournament``: par-time/qualifier scoring, leaderboard
assembly, balanced permalink selection, and (DEBUG-only) test-data population.
All persistence flows through :class:`AsyncTournamentRepository`; this module
imports no presentation/transport library.

The score cache and the cross-call calculation lock are module-level (services
are instantiated per call) so the locking/caching semantics match the original
shared-helper behavior. The pure scoring helpers and constants stay importable
at module scope (characterization tests target them directly).
"""

import asyncio
import datetime
import logging
import random
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import List, Optional

import aiocache

import config
from alttprbot import models
from alttprbot.repositories import AsyncTournamentRepository

# these should probably be in the database
QUALIFIER_MAX_SCORE = 105
QUALIFIER_MIN_SCORE = 0
MAX_POOL_IMBALANCE = 3

_CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)

_score_calculation_lock = asyncio.Lock()


def _utcnow() -> datetime.datetime:
    """Timezone-aware UTC now (drop-in for the old ``discord.utils.utcnow()``)."""
    return datetime.datetime.now(datetime.timezone.utc)


def average_timedelta(timedelta_list: List[timedelta]) -> timedelta:
    """Calculates the average of a list of timedeltas."""
    total_seconds = sum(t.total_seconds() for t in timedelta_list)
    average_seconds = total_seconds / len(timedelta_list)
    return timedelta(seconds=average_seconds)


def calculate_qualifier_score(par_time: timedelta, elapsed_time: timedelta) -> float:
    """
    Calculates a qualifier score based on the par time and elapsed time.
    The score is a percentage of the par time, with a maximum of 105% and a minimum of 0%.
    """
    return max(QUALIFIER_MIN_SCORE,
               min(QUALIFIER_MAX_SCORE, (2 - (elapsed_time.total_seconds() / par_time.total_seconds())) * 100))


@dataclass
class LeaderboardEntry:
    """
    Represents a leaderboard entry for a user.
    """
    player: models.Users
    races: List[models.AsyncTournamentRace]

    @cached_property
    def score(self) -> float:
        """
        Average score of all races.
        """
        scores = [
            r.score if r is not None and r.score is not None else 0
            for r in self.races
        ]
        return sum(scores) / len(scores)

    @cached_property
    def estimate(self) -> float:
        """
        Calculate the estimated score for a player, only averaging the races they've finished.
        """
        scores = [
            r.score
            for r in self.races if r is not None and r.status == "finished" and r.score is not None
        ]
        if not scores:
            return 0

        return sum(scores) / len(scores)

    @cached_property
    def score_formatted(self) -> str:
        """
        Formatted score suitable for web display.
        """
        return f"{self.score:.3f}"

    @cached_property
    def estimate_formatted(self) -> str:
        """
        Formatted estimate suitable for web display.
        """
        return f"{self.estimate:.3f}"

    @cached_property
    def finished_race_count(self) -> int:
        """
        Count of finished races.
        """
        return len([r for r in self.races if r is not None and r.status == "finished"])

    @cached_property
    def unattempted_race_count(self) -> int:
        """
        Count of unattempted races.
        """
        return len([r for r in self.races if r is None])

    @cached_property
    def forfeited_race_count(self) -> int:
        """
        Count of attempted, but forfeited, races.
        """
        return len([r for r in self.races if r is not None and r.status in ["forfeit", "disqualified"]])


class AsyncTournamentScoringService:
    def __init__(self) -> None:
        self.repository = AsyncTournamentRepository()

    async def calculate_async_tournament(
        self, tournament: models.AsyncTournament, only_approved: bool = False, cache: bool = True
    ) -> None:
        """
        Iterates through each permalink for a tournament and calculates the par time for each one.
        This is intended to be run as a background task.

        If only_approved is True, only approved runs will be used to calculate the par time.

        This function is thread-safe.
        """
        async with _score_calculation_lock:
            await self.repository.fetch_pools_with_permalinks(tournament)
            for pool in tournament.permalink_pools:
                for permalink in pool.permalinks:
                    await self.calculate_permalink_par(permalink, only_approved=only_approved)

        if cache:
            await _CACHE.delete(f'async_leaderboard_{tournament.id}')

    async def calculate_permalink_par(
        self, permalink: models.AsyncTournamentPermalink, only_approved: bool = False
    ) -> Optional[bool]:
        """
        Calculates the "par" time for a permalink by averaging the 5 fastest times.
        Write the par time to the Permalink record in the database, then write invidual scores

        Returns if the par time has changed.
        """
        # don't bother scoring reattempts, we also don't want them included in the average
        # (only score approved runs, if requested, off by default)
        races = await self.repository.list_races_for_par(permalink, only_approved=only_approved)

        finished_races = [r for r in races if r.status == "finished"]

        # sort by elapsed_time attribute
        finished_races.sort(key=lambda race: race.elapsed_time)

        if not finished_races:
            # no runs have been submitted, so we can't calculate a par time
            # skip this permalink until we have more data
            return

        # calculate the average of the 5 fastest times
        if len(races) < 5:
            top_finishes = finished_races
        else:
            top_finishes = finished_races[:5]

        par_time = average_timedelta([race.elapsed_time for race in top_finishes])

        await self.repository.save_permalink_par(
            permalink, float(par_time.total_seconds()), _utcnow()
        )

        for race in races:
            score = calculate_qualifier_score(
                par_time=par_time, elapsed_time=race.elapsed_time
            ) if race.status == "finished" else 0
            await self.repository.save_race_score(race, score, _utcnow())

        return True

    async def get_eligible_permalink_from_pool(
        self, pool: models.AsyncTournamentPermalinkPool, user: models.Users
    ) -> models.AsyncTournamentPermalink:
        """
        Gets an eligible permalink from a pool for a user to play.
        """
        await self.repository.fetch_pool_tournament_and_permalinks(pool)

        # get the number of times each permalink has been played
        permalink_counts = await self.repository.permalink_play_counts(pool)
        permalink_count_dict = {item['permalink_id']: item['count'] for item in permalink_counts}
        permalink_count_dict = {p.id: permalink_count_dict.get(p.id, 0) for p in pool.permalinks if p.live_race is False}

        # get the permalinks that the user has played
        player_async_history = await self.repository.list_player_pool_history(pool, user)

        # get the permalinks that are eligible to be played
        available_permalinks = await self.repository.list_available_permalinks(pool)
        played_permalinks = [p.permalink for p in player_async_history]
        eligible_permalinks = list(set(available_permalinks) - set(played_permalinks))

        if max(permalink_count_dict.values()) - min(permalink_count_dict.values()) > MAX_POOL_IMBALANCE:
            # pool is unbalanced, so we need to pick a permalink that has been played the least
            permalink_id = min(permalink_count_dict, key=permalink_count_dict.get)
            # ensure it's eligible to be played
            if permalink_id in [e.id for e in eligible_permalinks]:
                permalink = await self.repository.get_permalink_by_id(permalink_id)
                logging.info(
                    f"Pool {pool.id} is unbalanced, picking permalink {permalink.id} to force.  User {user.id} has played {len(played_permalinks)} permalinks, and {len(eligible_permalinks)} are eligible.")
            else:
                # pick a random eligible permalink instead of the one we need to force, because the one we're forcing is not eligible
                permalink: models.AsyncTournamentPermalink = random.choice(eligible_permalinks)
                logging.info(
                    f"Pool {pool.id} is unbalanced, but permalink {permalink_id} is not eligible.  Picking permalink {permalink.id} instead. User {user.id} has played {len(played_permalinks)} permalinks, and {len(eligible_permalinks)} are eligible.")
        else:
            permalink: models.AsyncTournamentPermalink = random.choice(eligible_permalinks)

        return permalink

    async def populate_test_data(
        self, tournament: models.AsyncTournament, participant_count: int = 1
    ) -> None:
        """
        Populates a tournament with test data for each permalink.
        Will use fake Discord User IDs for the racers that'll be in the range of 1 to 100000, which is smaller than a real ID.
        This should only be ran in a local testing environment.
        """
        # only run this in a local testing environment
        if not config.DEBUG:
            raise Exception("This function should only be ran in a local testing environment.")

        await self.repository.fetch_pools(tournament)

        # create specified number of fake users
        offset = random.randint(1, 1000) * 1000
        for i in range(1, participant_count + 1):
            # create a fake user, set a test_user flag to true so we can delete them later if needed
            user = await self.repository.create_test_user(
                i + offset, f"Test User {i + offset}"
            )
            # iterate through each pool in the tournament, using our existing algorithm to pick a permalink
            for pool in tournament.permalink_pools:
                permalink = await self.get_eligible_permalink_from_pool(pool, user)
                await self.repository.create_finished_test_race(
                    tournament=tournament,
                    user=user,
                    permalink=permalink,
                    thread_id=random.randint(1, 10000000000000),
                    thread_open_time=_utcnow(),
                    start_time=_utcnow(),
                    end_time=_utcnow() + timedelta(seconds=random.randint(3600000, 7200000) / 1000),
                )

    # TODO: this is an inefficient way to calculate the leaderboard, but it's the only way I can think of right now
    async def get_leaderboard(
        self, tournament: models.AsyncTournament, cache: bool = True
    ) -> List[LeaderboardEntry]:
        """
        Returns a leaderboard for the specified tournament.
        The leaderboard is a list of LeaderboardEntry objects, sorted by score.
        The pools are a list of the permalink pools for the tournament.
        This return of this coroutine is cached until scores are calculated.
        """
        key = f'async_leaderboard_{tournament.id}'
        if await _CACHE.exists(key) and cache:
            leaderboard = await _CACHE.get(key)
            return leaderboard

        async with _score_calculation_lock:
            # get a list of all user IDs who have participated in the tournament
            logging.info("Building leaderboard for tournament %s", tournament.id)
            user_id_list = await self.repository.list_participant_user_ids(tournament)

            # get a list of all permalink pools for the tournament
            await self.repository.fetch_pools(tournament)

            leaderboard: List[LeaderboardEntry] = []
            for user_id in user_id_list:
                rs = []
                for pool in tournament.permalink_pools:
                    races = await self.repository.list_user_pool_scored_races(user_id, tournament, pool)
                    for i in range(tournament.runs_per_pool):
                        try:
                            race = races[i]
                        except IndexError:
                            race = None
                        rs.append(race)

                entry = LeaderboardEntry(
                    player=await self.repository.get_user(user_id),
                    races=rs
                )
                leaderboard.append(entry)

            leaderboard.sort(key=lambda e: e.score, reverse=True)

        logging.info("Leaderboard built for tournament %s", tournament.id)
        await _CACHE.set(key, leaderboard)
        return leaderboard
