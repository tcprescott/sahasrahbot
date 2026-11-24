"""Tests for the services behind the racetime.gg handlers, against the in-memory
SQLite ``db``: alttprbot/services/spoiler_races.py and racetime_rooms.py.

The handler-level behaviour (chat replies, countdowns, room creation) is pinned in
tests/test_racetime_handlers.py; these pin the data each service stores and returns.
"""

from datetime import datetime, timedelta

import pytest

from alttprbot import models
from alttprbot.services import racetime_rooms, spoiler_races

ROOM = "alttpr/cool-room-1234"


async def test_spoiler_race_lifecycle(db):
    assert await spoiler_races.get(ROOM) is None

    first = await spoiler_races.schedule(ROOM, "https://spoilers.test/a", 600)
    second = await spoiler_races.schedule(ROOM, "https://spoilers.test/b", 900)
    assert first.id == second.id
    assert await models.SpoilerRaces.filter(srl_id=ROOM).count() == 1

    race = await spoiler_races.get(ROOM)
    assert (race.spoiler_url, race.studytime, race.started) == ("https://spoilers.test/b", 900, None)

    await spoiler_races.mark_started(race)
    assert (await spoiler_races.get(ROOM)).started is not None

    await spoiler_races.delete(race)
    assert await spoiler_races.get(ROOM) is None


async def test_unlisted_rooms_are_tracked_per_category(db):
    await racetime_rooms.set_unlisted(ROOM, "alttpr", True)
    await racetime_rooms.set_unlisted(ROOM, "alttpr", True)  # update_or_create, no duplicate
    await racetime_rooms.set_unlisted("smz3/other-room-1", "smz3", True)

    assert [r.room_name for r in await racetime_rooms.unlisted_rooms("alttpr")] == [ROOM]
    assert [r.room_name for r in await racetime_rooms.unlisted_rooms("smz3")] == ["smz3/other-room-1"]

    await racetime_rooms.set_unlisted(ROOM, "alttpr", False)
    assert await racetime_rooms.unlisted_rooms("alttpr") == []

    await racetime_rooms.forget_unlisted("smz3/other-room-1")
    assert not await models.RTGGUnlistedRooms.exists()


async def test_stream_override_status(db):
    assert await racetime_rooms.stream_override_status("u1", "alttpr") == racetime_rooms.OVERRIDE_NOT_WHITELISTED

    await models.RTGGOverrideWhitelist.create(racetime_id="u1", category="alttpr", expires=None)
    assert await racetime_rooms.stream_override_status("u1", "alttpr") == racetime_rooms.OVERRIDE_ALLOWED
    # whitelisting is per category
    assert await racetime_rooms.stream_override_status("u1", "smz3") == racetime_rooms.OVERRIDE_NOT_WHITELISTED


async def test_known_issue_stream_override_status_with_expiry_raises(db):
    """KNOWN ISSUE, pinned not endorsed: ``expires`` comes back timezone-aware and is
    compared with naive ``datetime.utcnow()``, so any entry with an expiry raises
    TypeError (see test_known_issue_override_with_expiry_date_crashes)."""
    await models.RTGGOverrideWhitelist.create(racetime_id="u1", category="alttpr", expires=datetime.utcnow() + timedelta(days=1))
    with pytest.raises(TypeError):
        await racetime_rooms.stream_override_status("u1", "alttpr")


async def test_tournament_race(db):
    assert await racetime_rooms.tournament_race(ROOM) is None
    await models.TournamentResults.create(srl_id=ROOM, episode_id="42", event="alttpr")
    assert await racetime_rooms.tournament_race(ROOM) == ("alttpr", "42")

