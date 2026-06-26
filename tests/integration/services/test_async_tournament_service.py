"""AsyncTournamentService integration tests: reads + pydantic serialization (live ORM)."""

import json

from alttprbot import models
from alttprbot.services import AsyncTournamentService


async def _make_tournament(name="Test Async", channel_id=100, active=True):
    return await models.AsyncTournament.create(
        name=name, guild_id=1, channel_id=channel_id, owner_id=3, active=active
    )


async def test_get_tournament_round_trip(tortoise_db):
    service = AsyncTournamentService()
    assert await service.get_tournament(999) is None

    tournament = await _make_tournament()
    fetched = await service.get_tournament(tournament.id)
    assert fetched is not None and fetched.name == "Test Async"


async def test_tournament_json_serializes(tortoise_db):
    service = AsyncTournamentService()
    tournament = await _make_tournament(name="Serialize Me")

    raw = await service.tournament_json(tournament.id)
    assert raw is not None
    payload = json.loads(raw)
    assert payload["name"] == "Serialize Me"

    assert await service.tournament_json(999) is None


async def test_tournaments_json_filters_active(tortoise_db):
    service = AsyncTournamentService()
    await _make_tournament(name="Active One", channel_id=101, active=True)
    await _make_tournament(name="Closed One", channel_id=102, active=False)

    active_names = {t["name"] for t in json.loads(await service.tournaments_json(True))}
    assert active_names == {"Active One"}

    all_names = {t["name"] for t in json.loads(await service.tournaments_json(None))}
    assert all_names == {"Active One", "Closed One"}
