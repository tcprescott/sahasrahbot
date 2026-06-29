"""Unit tests for the ALTTPR League orchestrator (PR5).

Covers the league-specific overrides: the external ``mode`` fetch, the dynamic
room-creation kwargs (solo / co-op / spoiler), the spoiler vs preset roll, the no-op
welcome, and the two definitions' ID transcription.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import alttprbot.services.tournament.alttprleague as league_mod
from alttprbot.services.tournament import SeedResult
from alttprbot.services.tournament.alttprleague import (
    INVITATIONAL_LEAGUE_DEFINITION,
    OPEN_LEAGUE_DEFINITION,
    ALTTPRLeagueOrchestrator,
)
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer

EPISODE = {
    "id": 100,
    "event": {"shortName": "League", "slug": "invleague"},
    "match1": {"title": "Round 1", "players": []},
    "channels": [],
    "whenCountdown": "2026-06-26T18:00:00-04:00",
    "when": "2026-06-26T18:30:00-04:00",
}


class _FakeSeed:
    code = ["Bow", "Boots"]
    url = "http://seed/permalink"


def _league_orch(*, racetime=None, league_data=None):
    orch = ALTTPRLeagueOrchestrator(
        INVITATIONAL_LEAGUE_DEFINITION, 100,
        presenter=AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=racetime or AsyncMock(),
    )
    orch.episode = EPISODE
    orch.players = [TournamentPlayer("rt1", "A", 1)]
    orch.tournament_game = None
    orch.room = RaceRoom(name="alttpr/room", url="http://rt/room", entrant_ids=[])
    orch.league_data = league_data
    return orch


# --- external league mode fetch ---

class _FakeResp:
    def __init__(self, data):
        self._data = data

    async def json(self):
        return self._data


class _FakeReqCM:
    def __init__(self, data):
        self._data = data

    async def __aenter__(self):
        return _FakeResp(self._data)

    async def __aexit__(self, *exc):
        return False


async def test_get_league_data_sets_mode(monkeypatch):
    captured = {}

    def fake_request(method, url, params=None):
        captured.update(method=method, url=url, params=params)
        return _FakeReqCM({"mode": {"preset": "open", "spoiler": False, "coop": False}})

    monkeypatch.setattr(league_mod.aiohttp, "request", fake_request)
    orch = _league_orch()
    await orch._get_league_data()

    assert orch.league_data == {"preset": "open", "spoiler": False, "coop": False}
    assert captured["url"] == "https://alttprleague.com/api/episode"
    assert captured["params"] == {"id": 100}


async def test_get_league_data_no_mode_messages_room(monkeypatch):
    monkeypatch.setattr(league_mod.aiohttp, "request", lambda *a, **k: _FakeReqCM({}))
    racetime = AsyncMock()
    orch = _league_orch(racetime=racetime)
    await orch._get_league_data()

    assert orch.league_data is None  # left unset on missing mode
    racetime.send_message.assert_awaited_once_with(
        "alttpr/room",
        "No active League mode!  This should not have happened.  Contact a league admin/mod for help.",
    )


# --- dynamic room-creation kwargs ---

def test_room_kwargs_solo():
    orch = _league_orch(league_data={"preset": "open", "spoiler": False, "coop": False})
    kw = orch.room_creation_kwargs
    assert kw["goal"] == "Beat the game - Tournament (Solo)"
    assert kw["team_race"] is False
    assert kw["require_even_teams"] is True
    # base kwargs preserved
    assert kw["invitational"] is True and kw["unlisted"] is False and kw["auto_start"] is True


def test_room_kwargs_coop():
    orch = _league_orch(league_data={"preset": "open", "spoiler": False, "coop": True})
    kw = orch.room_creation_kwargs
    assert kw["goal"] == "Beat the game - Tournament (Co-op)"
    assert kw["team_race"] is True
    assert kw["require_even_teams"] is True


def test_room_kwargs_spoiler():
    orch = _league_orch(league_data={"preset": "open", "spoiler": True, "coop": False})
    kw = orch.room_creation_kwargs
    assert kw["goal"] == "Beat the game - Spoiler"
    assert kw["team_race"] is False


# --- roll: preset vs spoiler ---

async def test_roll_non_spoiler_uses_preset(monkeypatch):
    preset_cls = MagicMock()
    preset_cls.return_value.generate = AsyncMock(return_value=_FakeSeed())
    monkeypatch.setattr(league_mod.generator, "ALTTPRPreset", preset_cls)

    orch = _league_orch(league_data={"preset": "openboots", "spoiler": False, "coop": False})
    result = await orch.roll()

    assert isinstance(result, SeedResult)
    preset_cls.assert_called_once_with("openboots")
    preset_cls.return_value.generate.assert_awaited_once_with(
        allow_quickswap=True, tournament=True, hints=False, spoilers="off"
    )


async def test_roll_spoiler_generates_and_schedules(monkeypatch):
    spoiler = MagicMock()
    spoiler.seed = _FakeSeed()
    spoiler.spoiler_log_url = "http://spoiler/log"
    monkeypatch.setattr(league_mod.spoilers, "generate_spoiler_game", AsyncMock(return_value=spoiler))

    racetime = AsyncMock()
    orch = _league_orch(racetime=racetime, league_data={"preset": "spoilerpreset", "spoiler": True, "coop": False})
    result = await orch.roll()

    league_mod.spoilers.generate_spoiler_game.assert_awaited_once_with("spoilerpreset")
    racetime.schedule_spoiler_race.assert_awaited_once_with(
        "alttpr/room", spoiler_url="http://spoiler/log", studytime=0
    )
    assert result.seed is spoiler.seed


# --- no-op welcome (league suppresses the ALTTPR welcome + pinned action) ---

async def test_send_room_welcome_is_noop():
    racetime = AsyncMock()
    orch = _league_orch(racetime=racetime)
    await orch.send_room_welcome()
    racetime.send_message.assert_not_awaited()
    racetime.send_pinned_action.assert_not_awaited()


# --- definitions ---

def test_league_definitions_share_config_differ_only_in_slug():
    inv, opn = INVITATIONAL_LEAGUE_DEFINITION, OPEN_LEAGUE_DEFINITION
    assert inv.event_slug == "invleague" and opn.event_slug == "alttprleague"
    for d in (inv, opn):
        assert d.racetime_category == "alttpr"
        assert d.racetime_goal == "Beat the game - Tournament (Solo)"
        assert d.guild_id == 543577975032119296
        assert d.audit_channel_id == 546728638272241674
        assert d.commentary_channel_id == 1157407211094556703
        assert d.helper_role_ids == [543596853871116288, 543597099649073162, 676530377812082706, 553295025190993930, 674109759179194398]
        assert d.stream_delay == 10
        assert d.create_scheduled_events is True
    # independent helper-role lists (factory copies the module constant)
    assert inv.helper_role_ids is not opn.helper_role_ids
