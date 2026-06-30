"""Round-trip tests for the RaceTime repositories against in-memory SQLite.

See alttprbot/repositories/{spoiler_race,race_room,tournament_results}_repository.py.
"""

from datetime import datetime, timezone

from alttprbot import models
from alttprbot.repositories import (
    RaceRoomRepository,
    SpoilerRaceRepository,
    TournamentGamesRepository,
    TournamentResultsRepository,
)


async def test_spoiler_race_upsert_get_mark_delete(tortoise_db):
    assert await SpoilerRaceRepository.get_by_srl_id("room-1") is None

    race, created = await SpoilerRaceRepository.upsert(
        srl_id="room-1", spoiler_url="http://x", studytime=900
    )
    assert created is True
    assert race.spoiler_url == "http://x"

    when = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    await SpoilerRaceRepository.mark_started(race, when)
    refetched = await SpoilerRaceRepository.get_by_srl_id("room-1")
    assert refetched.started == when

    await SpoilerRaceRepository.delete_instance(refetched)
    assert await SpoilerRaceRepository.get_by_srl_id("room-1") is None


async def test_unlisted_room_set_list_clear(tortoise_db):
    await RaceRoomRepository.set_unlisted("room-1", "alttpr")
    await RaceRoomRepository.set_unlisted("room-2", "alttpr")
    await RaceRoomRepository.set_unlisted("room-3", "smz3")

    rooms = await RaceRoomRepository.list_unlisted_for_category("alttpr")
    assert {r.room_name for r in rooms} == {"room-1", "room-2"}

    # update_or_create updates in place (no duplicate)
    await RaceRoomRepository.set_unlisted("room-1", "alttpr")
    assert len(await RaceRoomRepository.list_unlisted_for_category("alttpr")) == 2

    deleted = await RaceRoomRepository.clear_unlisted("room-1")
    assert deleted == 1
    assert {r.room_name for r in await RaceRoomRepository.list_unlisted_for_category("alttpr")} == {"room-2"}


async def test_override_whitelist_lookup(tortoise_db):
    assert await RaceRoomRepository.get_override_whitelist("rtid", "alttpr") is None

    await models.RTGGOverrideWhitelist.create(racetime_id="rtid", category="alttpr")
    found = await RaceRoomRepository.get_override_whitelist("rtid", "alttpr")
    assert found is not None
    # wrong category does not match
    assert await RaceRoomRepository.get_override_whitelist("rtid", "smz3") is None


async def test_tournament_results_get_by_srl_id(tortoise_db):
    assert await TournamentResultsRepository.get_by_srl_id("room-1") is None
    await models.TournamentResults.create(srl_id="room-1", event="test")
    found = await TournamentResultsRepository.get_by_srl_id("room-1")
    assert found is not None and found.event == "test"


async def test_tournament_results_upsert_by_srl_id(tortoise_db):
    row, created = await TournamentResultsRepository.upsert_by_srl_id(
        "room-1", {"episode_id": "42", "event": "alttpr", "spoiler": None}
    )
    assert created is True and row.event == "alttpr"

    row2, created2 = await TournamentResultsRepository.upsert_by_srl_id(
        "room-1", {"event": "smz3"}
    )
    assert created2 is False and row2.id == row.id
    refetched = await TournamentResultsRepository.get_by_srl_id("room-1")
    assert refetched.event == "smz3" and refetched.episode_id == "42"


async def test_tournament_results_create_or_update_with_permalink(tortoise_db):
    # creates the row, then stamps the permalink
    row = await TournamentResultsRepository.create_or_update_with_permalink(
        srl_id="room-9",
        defaults={"episode_id": "7", "event": "boots", "spoiler": None},
        permalink="http://alttpr/permalink1",
    )
    assert row.event == "boots"
    assert row.permalink == "http://alttpr/permalink1"

    refetched = await TournamentResultsRepository.get_by_srl_id("room-9")
    assert refetched.permalink == "http://alttpr/permalink1"
    assert refetched.episode_id == "7"

    # second call updates in place (no duplicate) and re-stamps the permalink
    row2 = await TournamentResultsRepository.create_or_update_with_permalink(
        srl_id="room-9",
        defaults={"event": "boots", "spoiler": None},
        permalink="http://alttpr/permalink2",
    )
    assert row2.id == row.id
    refetched2 = await TournamentResultsRepository.get_by_srl_id("room-9")
    assert refetched2.permalink == "http://alttpr/permalink2"
    assert refetched2.episode_id == "7"  # untouched default preserved


async def test_tournament_games_get_and_upsert(tortoise_db):
    assert await TournamentGamesRepository.get_by_episode_id("99") is None

    row, created = await TournamentGamesRepository.upsert_by_episode_id(
        "99", {"event": "alttpr", "submitted": 1}
    )
    assert created is True and row.submitted == 1

    fetched = await TournamentGamesRepository.get_by_episode_id("99")
    assert fetched is not None and fetched.event == "alttpr"
