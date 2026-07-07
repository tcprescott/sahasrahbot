"""Round-trip tests for the async-tournament repo methods added for the discord cog."""

from alttprbot import models
from alttprbot.repositories import (
    AsyncTournamentLiveRaceRepository,
    AsyncTournamentPermissionsRepository,
    AsyncTournamentRepository,
)


async def _tournament(channel_id=500):
    return await AsyncTournamentRepository.create_tournament(
        name="T", report_channel_id=None, active=True, guild_id=1,
        channel_id=channel_id, owner_id=2,
    )


async def test_tournament_pool_permalink_race_chain(tortoise_db):
    tournament = await _tournament(channel_id=501)
    assert (await AsyncTournamentRepository.get_by_channel_id(501)).id == tournament.id
    assert await AsyncTournamentRepository.get_by_channel_id(999) is None
    assert [t.id for t in await AsyncTournamentRepository.list_active()] == [tournament.id]

    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    assert (await AsyncTournamentRepository.get_pool_by_name(tournament, "A")).id == pool.id

    permalink = await AsyncTournamentRepository.create_permalink(
        pool=pool, url="http://x", notes="abc", live_race=False
    )
    user = await models.Users.create(discord_user_id=42)

    race = await AsyncTournamentRepository.create_race(
        tournament=tournament, user=user, permalink=permalink,
        thread_id=777, thread_open_time=None,
    )
    fetched = await AsyncTournamentRepository.get_race_by_thread_id(777)
    assert fetched is not None and fetched.id == race.id

    with_user = await AsyncTournamentRepository.get_race_by_thread_id_with_user(777)
    assert with_user.user.discord_user_id == 42


async def test_permissions_get_or_create(tortoise_db):
    tournament = await _tournament(channel_id=502)
    user = await models.Users.create(discord_user_id=7)

    assert await AsyncTournamentPermissionsRepository.get_permission(tournament, user, "admin") is None
    created = await AsyncTournamentPermissionsRepository.create_permission(tournament, user, "admin")
    found = await AsyncTournamentPermissionsRepository.get_permission(tournament, user, "admin")
    assert found is not None and found.id == created.id
    # role-scoped
    assert await AsyncTournamentPermissionsRepository.get_permission(tournament, user, "mod") is None


async def test_live_race_lookup_and_slug_search(tortoise_db):
    tournament = await _tournament(channel_id=503)
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")

    await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, racetime_slug="alttpr/clever-cat", status="in_progress"
    )
    await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, racetime_slug="alttpr/sleepy-dog", status="finished"
    )

    found = await AsyncTournamentLiveRaceRepository.get_by_racetime_slug("alttpr/clever-cat")
    assert found is not None
    assert await AsyncTournamentLiveRaceRepository.get_by_racetime_slug("nope") is None

    # autocomplete returns only in-progress slugs matching the partial
    slugs = {r["racetime_slug"] for r in await AsyncTournamentLiveRaceRepository.list_in_progress_slugs("cat")}
    assert slugs == {"alttpr/clever-cat"}
    assert await AsyncTournamentLiveRaceRepository.list_in_progress_slugs("dog") == []


async def test_get_by_channel_id_with_pools(tortoise_db):
    tournament = await _tournament(channel_id=504)
    await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    await AsyncTournamentRepository.create_pool(tournament=tournament, name="B", preset="casualboots")

    fetched = await AsyncTournamentRepository.get_by_channel_id_with_pools(504)
    assert fetched.id == tournament.id
    # relation is hydrated — iterable without a further fetch_related
    assert {p.name for p in fetched.permalink_pools} == {"A", "B"}

    # unknown channel returns None (regression: the None guard must run before any relation access)
    assert await AsyncTournamentRepository.get_by_channel_id_with_pools(999) is None


async def test_get_by_racetime_slug_with_tournament(tortoise_db):
    tournament = await _tournament(channel_id=505)
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    await models.AsyncTournamentLiveRace.create(
        tournament=tournament, pool=pool, racetime_slug="alttpr/brave-fox", status="in_progress"
    )

    live_race = await AsyncTournamentLiveRaceRepository.get_by_racetime_slug_with_tournament("alttpr/brave-fox")
    assert live_race.tournament.id == tournament.id

    assert await AsyncTournamentLiveRaceRepository.get_by_racetime_slug_with_tournament("nope") is None


async def test_get_race_with_user(tortoise_db):
    tournament = await _tournament(channel_id=506)
    pool = await AsyncTournamentRepository.create_pool(tournament=tournament, name="A", preset="open")
    permalink = await AsyncTournamentRepository.create_permalink(
        pool=pool, url="http://x", notes="abc", live_race=False
    )
    user = await models.Users.create(discord_user_id=43)
    race = await AsyncTournamentRepository.create_race(
        tournament=tournament, user=user, permalink=permalink,
        thread_id=778, thread_open_time=None,
    )

    fetched = await AsyncTournamentRepository.get_race_with_user(race.id, tournament)
    assert fetched.user.discord_user_id == 43

    assert await AsyncTournamentRepository.get_race_with_user(999999, tournament) is None
