"""Round-trip tests for the AsyncTournament repo methods added for the alttpr_quals roll."""

from datetime import datetime, timezone

from alttprbot import models
from alttprbot.repositories import (
    AsyncTournamentLiveRaceRepository,
    AsyncTournamentRepository,
    UserRepository,
)


async def _tournament(channel_id):
    return await AsyncTournamentRepository.create_tournament(
        name="T", report_channel_id=None, active=True, guild_id=1,
        channel_id=channel_id, owner_id=2,
    )


async def test_live_race_by_episode_relations_and_permalink_slug(tortoise_db):
    tournament = await _tournament(601)
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    live = await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, episode_id=900, status="scheduled"
    )

    assert (await AsyncTournamentLiveRaceRepository.get_by_episode_id(900)).id == live.id
    assert await AsyncTournamentLiveRaceRepository.get_by_episode_id(999) is None

    with_rel = await AsyncTournamentLiveRaceRepository.get_by_episode_id_with_relations(900)
    assert with_rel.pool.id == pool.id and with_rel.tournament.id == tournament.id
    assert with_rel.permalink is None

    permalink = await AsyncTournamentRepository.create_live_permalink(
        url="http://seed", pool=pool, notes="live note"
    )
    assert permalink.live_race is True and permalink.url == "http://seed"

    await AsyncTournamentLiveRaceRepository.set_permalink_and_slug(live, permalink, "alttpr/room")
    refetched = await AsyncTournamentLiveRaceRepository.get_by_episode_id_with_relations(900)
    assert refetched.permalink.id == permalink.id
    assert refetched.racetime_slug == "alttpr/room"


async def test_pool_run_count_and_active_race_and_pending_entry(tortoise_db):
    tournament = await _tournament(602)  # runs_per_pool defaults to 1
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    permalink = await AsyncTournamentRepository.create_live_permalink(url="http://s", pool=pool, notes="n")
    live = await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, episode_id=901, status="scheduled"
    )
    user = await models.Users.create(rtgg_id="rtA", display_name="A")

    assert await AsyncTournamentRepository.count_completed_pool_races(tournament, user, pool) == 0
    assert await AsyncTournamentRepository.user_has_active_race(tournament, user) is False

    entry = await AsyncTournamentRepository.create_pending_live_entry(tournament, permalink, user, live)
    assert entry.status == "pending" and entry.thread_id is None

    # the pending entry is an active race, and counts toward the pool run total
    assert await AsyncTournamentRepository.user_has_active_race(tournament, user) is True
    assert await AsyncTournamentRepository.count_completed_pool_races(tournament, user, pool) == 1

    # reattempted races do not count toward the pool total
    entry.reattempted = True
    await entry.save()
    assert await AsyncTournamentRepository.count_completed_pool_races(tournament, user, pool) == 0


async def test_process_race_start_promotes_present_and_prunes_absent(tortoise_db):
    tournament = await _tournament(603)
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    permalink = await AsyncTournamentRepository.create_live_permalink(url="http://s", pool=pool, notes="n")
    live = await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, episode_id=902, status="pending"
    )
    present = await models.Users.create(rtgg_id="rtPresent", display_name="Present")
    absent = await models.Users.create(rtgg_id="rtAbsent", display_name="Absent")
    for u in (present, absent):
        await AsyncTournamentRepository.create_pending_live_entry(tournament, permalink, u, live)

    start = datetime(2026, 6, 26, 22, 0, tzinfo=timezone.utc)
    names = await AsyncTournamentLiveRaceRepository.process_race_start(live, ["rtPresent"], start)

    assert names == ["Present"]  # only the present runner is in-progress
    # present -> in_progress with start_time; absent pending row deleted
    present_race = await models.AsyncTournamentRace.get(user=present, live_race=live)
    assert present_race.status == "in_progress" and present_race.start_time == start
    assert await models.AsyncTournamentRace.filter(user=absent, live_race=live).count() == 0
    # live race itself marked in_progress
    refetched = await AsyncTournamentLiveRaceRepository.get_by_episode_id(902)
    assert refetched.status == "in_progress"


async def test_user_get_or_create_by_rtgg_and_set_twitch(tortoise_db):
    user, created = await UserRepository.get_or_create_by_rtgg_id(
        "rtX", defaults={"display_name": "X", "twitch_name": "tx"}
    )
    assert created is True and user.display_name == "X" and user.twitch_name == "tx"

    again, created2 = await UserRepository.get_or_create_by_rtgg_id(
        "rtX", defaults={"display_name": "ignored", "twitch_name": "ignored"}
    )
    assert created2 is False and again.id == user.id  # existing row, defaults ignored

    await UserRepository.set_twitch_name(again, "newtwitch")
    refetched = await UserRepository.get_by_rtgg_id("rtX")
    assert refetched.twitch_name == "newtwitch"
