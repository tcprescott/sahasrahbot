"""Characterization tests for async tournament scoring (alttprbot/util/asynctournament.py).

These pin what the code does on master today, so the async tournament service
refactor can be checked against them. Where today's behaviour looks wrong, the
test says so in its name and docstring ("KNOWN ISSUE") instead of claiming it
is correct. Change those tests deliberately when the behaviour is fixed.
"""

import random
from datetime import datetime, timedelta, timezone

import pytest

from alttprbot import models
from alttprbot.util import asynctournament as at

T0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_average_timedelta():
    assert at.average_timedelta([timedelta(minutes=60), timedelta(minutes=90)]) == timedelta(minutes=75)


def test_average_timedelta_empty_list_raises():
    with pytest.raises(ZeroDivisionError):
        at.average_timedelta([])


@pytest.mark.parametrize(
    "elapsed_minutes, expected",
    [
        (100, 100.0),  # exactly par
        (110, 90.0),  # 10% slower
        (90, 105.0),  # 10% faster would be 110, capped at the max of 105
        (95, 105.0),  # exactly at the cap
        (200, 0.0),  # twice par is 0
        (300, 0.0),  # slower than twice par is floored at 0
    ],
)
def test_calculate_qualifier_score(elapsed_minutes, expected):
    score = at.calculate_qualifier_score(
        par_time=timedelta(minutes=100), elapsed_time=timedelta(minutes=elapsed_minutes)
    )
    assert score == pytest.approx(expected)


def test_score_constants():
    assert (at.QUALIFIER_MIN_SCORE, at.QUALIFIER_MAX_SCORE, at.MAX_POOL_IMBALANCE) == (0, 105, 3)


# ---------------------------------------------------------------------------
# Fixtures for DB-backed tests
# ---------------------------------------------------------------------------


_user_seq = 0


async def make_user(name=None):
    global _user_seq
    _user_seq += 1
    return await models.Users.create(
        discord_user_id=1000 + _user_seq, display_name=name or f"player{_user_seq}"
    )


async def make_tournament(pools=1, permalinks_per_pool=2, runs_per_pool=1, **kwargs):
    tournament = await models.AsyncTournament.create(
        name="Test Async",
        guild_id=1,
        channel_id=random.randint(1, 10**12),
        owner_id=1,
        runs_per_pool=runs_per_pool,
        **kwargs,
    )
    created_pools = []
    for p in range(pools):
        pool = await models.AsyncTournamentPermalinkPool.create(tournament=tournament, name=f"pool{p}")
        for i in range(permalinks_per_pool):
            await models.AsyncTournamentPermalink.create(pool=pool, url=f"https://example.test/{p}/{i}")
        created_pools.append(pool)
    return tournament, created_pools


async def make_race(tournament, permalink, user, minutes=None, status="finished", **kwargs):
    fields = dict(tournament=tournament, permalink=permalink, user=user, status=status)
    if minutes is not None:
        fields["start_time"] = T0
        fields["end_time"] = T0 + timedelta(minutes=minutes)
    fields.update(kwargs)
    return await models.AsyncTournamentRace.create(**fields)


# ---------------------------------------------------------------------------
# calculate_permalink_par
# ---------------------------------------------------------------------------


async def test_par_is_average_of_five_fastest_finishes_and_scores_every_run(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]

    finishes = [100, 60, 80, 70, 90, 200]  # five fastest: 60..100, average 80
    races = [await make_race(tournament, permalink, await make_user(), minutes=m) for m in finishes]
    forfeit = await make_race(tournament, permalink, await make_user(), status="forfeit")
    dq = await make_race(tournament, permalink, await make_user(), status="disqualified")
    pending = await make_race(tournament, permalink, await make_user(), status="pending")
    in_progress = await make_race(tournament, permalink, await make_user(), status="in_progress", start_time=T0)

    changed = await at.calculate_permalink_par(permalink)
    assert changed is True

    await permalink.refresh_from_db()
    assert permalink.par_time == pytest.approx(80 * 60)
    assert permalink.par_updated_at is not None

    scores = {}
    for race in races + [forfeit, dq, pending, in_progress]:
        await race.refresh_from_db()
        scores[race.id] = race.score

    by_minutes = dict(zip(finishes, races))
    assert scores[by_minutes[80].id] == pytest.approx(100)
    assert scores[by_minutes[90].id] == pytest.approx(87.5)
    assert scores[by_minutes[60].id] == pytest.approx(105)  # (2 - 0.75) * 100 = 125, capped
    assert scores[by_minutes[200].id] == pytest.approx(0)  # slower than 2x par
    assert scores[forfeit.id] == 0
    assert scores[dq.id] == 0
    # pending / in-progress runs are not part of the query and are left unscored
    assert scores[pending.id] is None
    assert scores[in_progress.id] is None


async def test_par_with_fewer_than_five_finishes_uses_all_of_them(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]
    await make_race(tournament, permalink, await make_user(), minutes=60)
    await make_race(tournament, permalink, await make_user(), minutes=120)

    await at.calculate_permalink_par(permalink)
    await permalink.refresh_from_db()
    assert permalink.par_time == pytest.approx(90 * 60)


async def test_par_ignores_reattempted_runs(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]
    await make_race(tournament, permalink, await make_user(), minutes=100)
    reattempted = await make_race(tournament, permalink, await make_user(), minutes=10, reattempted=True)

    await at.calculate_permalink_par(permalink)
    await permalink.refresh_from_db()
    await reattempted.refresh_from_db()
    assert permalink.par_time == pytest.approx(100 * 60)
    assert reattempted.score is None


async def test_par_without_finishes_returns_none_and_writes_nothing(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]
    forfeit = await make_race(tournament, permalink, await make_user(), status="forfeit")

    assert await at.calculate_permalink_par(permalink) is None

    await permalink.refresh_from_db()
    await forfeit.refresh_from_db()
    assert permalink.par_time is None
    assert forfeit.score is None


async def test_only_approved_uses_review_status_approved(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]
    await make_race(tournament, permalink, await make_user(), minutes=100, review_status="approved")
    await make_race(tournament, permalink, await make_user(), minutes=50, review_status="pending")

    await at.calculate_permalink_par(permalink, only_approved=True)
    await permalink.refresh_from_db()
    assert permalink.par_time == pytest.approx(100 * 60)


async def test_known_issue_only_approved_ignores_runs_the_review_form_marks_accepted(db):
    """KNOWN ISSUE, pinned not endorsed.

    The web review form (asynctournament_race_view.html) saves
    ``review_status="accepted"``, and ``review_status_formatted`` understands
    "accepted", but ``calculate_permalink_par(only_approved=True)`` filters on
    "approved". So with only_approved, a reviewed-and-accepted run is not
    counted, and a pool where every run was accepted gets no par at all.
    Decide which word is right before changing this test.
    """
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    permalink = (await pool.permalinks.all())[0]
    accepted = await make_race(tournament, permalink, await make_user(), minutes=100, review_status="accepted")

    assert await at.calculate_permalink_par(permalink, only_approved=True) is None

    await permalink.refresh_from_db()
    await accepted.refresh_from_db()
    assert permalink.par_time is None
    assert accepted.score is None


async def test_calculate_async_tournament_scores_every_pool_and_clears_leaderboard_cache(db):
    tournament, pools = await make_tournament(pools=2, permalinks_per_pool=1)
    user = await make_user()
    permalinks = [(await p.permalinks.all())[0] for p in pools]
    for pl in permalinks:
        await make_race(tournament, pl, user, minutes=100)

    await at.CACHE.set(f"async_leaderboard_{tournament.id}", ["stale"])

    await at.calculate_async_tournament(tournament)

    for pl in permalinks:
        await pl.refresh_from_db()
        assert pl.par_time == pytest.approx(100 * 60)
    assert not await at.CACHE.exists(f"async_leaderboard_{tournament.id}")


async def test_calculate_async_tournament_cache_false_keeps_cache(db):
    tournament, _ = await make_tournament(pools=1, permalinks_per_pool=1)
    await at.CACHE.set(f"async_leaderboard_{tournament.id}", ["stale"])
    await at.calculate_async_tournament(tournament, cache=False)
    assert await at.CACHE.get(f"async_leaderboard_{tournament.id}") == ["stale"]


# ---------------------------------------------------------------------------
# get_eligible_permalink_from_pool
# ---------------------------------------------------------------------------


async def test_eligible_permalink_is_one_the_player_has_not_played(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=3)
    permalinks = await pool.permalinks.all()
    user = await make_user()
    await make_race(tournament, permalinks[0], user, minutes=90)
    await make_race(tournament, permalinks[1], user, minutes=90)

    for _ in range(10):
        chosen = await at.get_eligible_permalink_from_pool(pool, user)
        assert chosen.id == permalinks[2].id


async def test_eligible_permalink_skips_live_race_permalinks(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=2)
    permalinks = await pool.permalinks.all()
    permalinks[0].live_race = True
    await permalinks[0].save()

    for _ in range(10):
        chosen = await at.get_eligible_permalink_from_pool(pool, await make_user())
        assert chosen.id == permalinks[1].id


async def test_unbalanced_pool_forces_least_played_permalink(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=3)
    p0, p1, p2 = await pool.permalinks.all()
    # p0 played 4 times, p1 once, p2 never: max - min = 4 > MAX_POOL_IMBALANCE
    for _ in range(4):
        await make_race(tournament, p0, await make_user(), minutes=90)
    await make_race(tournament, p1, await make_user(), minutes=90)

    for _ in range(10):
        chosen = await at.get_eligible_permalink_from_pool(pool, await make_user())
        assert chosen.id == p2.id


async def test_unbalanced_pool_falls_back_to_random_when_forced_permalink_already_played(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=3)
    p0, p1, p2 = await pool.permalinks.all()
    for _ in range(4):
        await make_race(tournament, p0, await make_user(), minutes=90)
    await make_race(tournament, p1, await make_user(), minutes=90)
    user = await make_user()
    await make_race(tournament, p2, user, minutes=90)  # user already played the least-played one

    seen = {(await at.get_eligible_permalink_from_pool(pool, user)).id for _ in range(30)}
    assert seen <= {p0.id, p1.id}
    assert p2.id not in seen


async def test_balanced_pool_counts_imbalance_of_exactly_three_as_balanced(db):
    tournament, (pool,) = await make_tournament(permalinks_per_pool=2)
    p0, p1 = await pool.permalinks.all()
    for _ in range(3):
        await make_race(tournament, p0, await make_user(), minutes=90)

    random.seed(1)
    seen = {(await at.get_eligible_permalink_from_pool(pool, await make_user())).id for _ in range(30)}
    assert seen == {p0.id, p1.id}


async def test_known_issue_player_who_played_every_permalink_gets_index_error(db):
    """KNOWN ISSUE, pinned not endorsed: no eligible permalink raises IndexError
    from ``random.choice([])`` instead of a user-facing error. Callers are
    expected to check first."""
    tournament, (pool,) = await make_tournament(permalinks_per_pool=1)
    (p0,) = await pool.permalinks.all()
    user = await make_user()
    await make_race(tournament, p0, user, minutes=90)

    with pytest.raises(IndexError):
        await at.get_eligible_permalink_from_pool(pool, user)


# ---------------------------------------------------------------------------
# LeaderboardEntry
# ---------------------------------------------------------------------------


class _Race:
    def __init__(self, status, score):
        self.status = status
        self.score = score


def test_leaderboard_entry_counts_and_scores():
    races = [
        _Race("finished", 100.0),
        _Race("finished", 80.0),
        _Race("forfeit", 0),
        _Race("disqualified", 0),
        None,  # unattempted slot
        _Race("finished", None),  # finished but not yet scored
    ]
    entry = at.LeaderboardEntry(player=None, races=races)

    assert entry.score == pytest.approx(180 / 6)  # unplayed and unscored count as 0
    assert entry.estimate == pytest.approx(90)  # only scored finishes
    assert entry.score_formatted == "30.000"
    assert entry.estimate_formatted == "90.000"
    assert entry.finished_race_count == 3
    assert entry.unattempted_race_count == 1
    assert entry.forfeited_race_count == 2


def test_leaderboard_entry_with_no_finishes():
    entry = at.LeaderboardEntry(player=None, races=[None, _Race("forfeit", 0)])
    assert entry.score == 0
    assert entry.estimate == 0
    assert entry.estimate_formatted == "0.000"


# ---------------------------------------------------------------------------
# get_leaderboard
# ---------------------------------------------------------------------------


async def test_leaderboard_sorted_by_score_with_unplayed_slots(db):
    tournament, pools = await make_tournament(pools=2, permalinks_per_pool=1)
    pl_a, pl_b = [(await p.permalinks.all())[0] for p in pools]
    fast, slow = await make_user("fast"), await make_user("slow")

    await make_race(tournament, pl_a, fast, minutes=90, score=100.0)
    await make_race(tournament, pl_b, fast, minutes=90, score=90.0)
    await make_race(tournament, pl_a, slow, minutes=120, score=50.0)
    # slow has not played pool b; a pending race there does not count
    await make_race(tournament, pl_b, slow, status="pending")

    board = await at.get_leaderboard(tournament)

    assert [e.player.display_name for e in board] == ["fast", "slow"]
    assert board[0].score == pytest.approx(95)
    assert board[1].score == pytest.approx(25)
    assert board[1].races[1] is None
    assert board[1].unattempted_race_count == 1


async def test_leaderboard_runs_per_pool_gives_that_many_slots(db):
    tournament, (pool,) = await make_tournament(pools=1, permalinks_per_pool=2, runs_per_pool=2)
    p0, p1 = await pool.permalinks.all()
    user = await make_user()
    await make_race(tournament, p0, user, minutes=90, score=100.0)

    (entry,) = await at.get_leaderboard(tournament)
    assert len(entry.races) == 2
    assert entry.races[1] is None
    assert entry.score == pytest.approx(50)


async def test_leaderboard_excludes_reattempted_runs(db):
    tournament, (pool,) = await make_tournament(pools=1, permalinks_per_pool=2)
    p0, p1 = await pool.permalinks.all()
    user = await make_user()
    await make_race(tournament, p0, user, minutes=90, score=10.0, reattempted=True)
    await make_race(tournament, p1, user, minutes=90, score=100.0)

    (entry,) = await at.get_leaderboard(tournament)
    assert entry.score == pytest.approx(100)


async def test_leaderboard_is_cached_until_scores_recalculated(db):
    tournament, (pool,) = await make_tournament(pools=1, permalinks_per_pool=2)
    p0, p1 = await pool.permalinks.all()
    await make_race(tournament, p0, await make_user("first"), minutes=90, score=100.0)

    board = await at.get_leaderboard(tournament)
    assert len(board) == 1

    await make_race(tournament, p1, await make_user("second"), minutes=90, score=100.0)
    assert len(await at.get_leaderboard(tournament)) == 1  # served from cache
    assert len(await at.get_leaderboard(tournament, cache=False)) == 2

    await at.calculate_async_tournament(tournament)  # clears the cache
    assert len(await at.get_leaderboard(tournament)) == 2


async def test_populate_test_data_refuses_outside_debug(db, monkeypatch):
    import config

    tournament, _ = await make_tournament()
    monkeypatch.setattr(config, "DEBUG", False)
    with pytest.raises(Exception, match="local testing"):
        await at.populate_test_data(tournament)
