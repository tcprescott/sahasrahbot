"""Unit tests for the ALTTPR live-qualifier orchestrator (PR8).

The qualifier is the most entangled handler (live-race + AsyncTournament). All repositories,
the racetime gateway, the presenter, and the authz callback are mocked; the tests pin the
room-creation gate, room kwargs, race-info, the !tournamentrace guard ladder + happy path,
the eligible-entrant writes, and the race-start processing.
"""

from unittest.mock import AsyncMock

import pytest

import alttprbot.services.tournament.alttpr_quals as quals_mod
from alttprbot.services.tournament.alttpr_quals import (
    QUALIFIER_DEFINITION,
    ALTTPRQualifierOrchestrator,
)
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.types import RaceRoom

EPISODE = {
    "id": 100,
    "event": {"shortName": "Quals", "slug": "alttpr"},
    "match1": {"title": "Qualifier 1", "players": []},
    "channels": [{"name": "restreamA"}],
    "whenCountdown": "2026-06-26T18:00:00-04:00",
    "when": "2026-06-26T18:30:00-04:00",
}


class _Pool:
    def __init__(self, preset="open_preset"):
        self.preset = preset


class _Tournament:
    def __init__(self, runs_per_pool=2):
        self.runs_per_pool = runs_per_pool


class _LiveRace:
    def __init__(self, permalink=None, pool=None, tournament=None):
        self.permalink = permalink
        self.pool = pool
        self.tournament = tournament


class _Seed:
    url = "http://alttpr/seed"
    code = ["Bow", "Boots", "Bombs"]


def _orch(*, presenter=None, racetime=None, authz=None):
    orch = ALTTPRQualifierOrchestrator(
        QUALIFIER_DEFINITION, 100,
        presenter=presenter or AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=racetime or AsyncMock(),
        async_authz_checker=authz or AsyncMock(return_value=True),
    )
    orch.episode = EPISODE
    orch.room = RaceRoom(name="alttpr/quals", url="http://rt/alttpr/quals", entrant_ids=[])
    return orch


def _patch_update_data(orch, monkeypatch):
    monkeypatch.setattr(quals_mod.speedgaming, "get_episode", AsyncMock(return_value=EPISODE))
    monkeypatch.setattr(quals_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=None))
    orch.racetime.get_team = AsyncMock(return_value={"members": []})


# --- structure ---

def test_qualifier_extends_base():
    assert ALTTPRQualifierOrchestrator.__mro__[1] is TournamentOrchestrator


def test_room_kwargs():
    orch = _orch()
    kw = orch.room_creation_kwargs
    assert kw["invitational"] is False
    assert kw["start_delay"] == 30
    assert kw["auto_start"] is False
    assert kw["allow_prerace_chat"] is False
    assert kw["allow_midrace_chat"] is False
    assert kw["team_race"] is False  # base default


def test_race_info():
    orch = _orch()
    info = orch.race_info
    assert info.startswith("ALTTPR Main Tournament Live Qualifier - Qualifier 1 at ")
    assert "Seed Distributed and Room Locked at " in info
    assert " on restreamA" in info
    assert info.endswith(" - 100")


def test_definition():
    d = QUALIFIER_DEFINITION
    assert d.event_slug == "alttpr" and d.racetime_category == "alttpr"
    assert d.racetime_goal == "Beat the game - Tournament (Solo)"
    assert d.guild_id == 334795604918272012
    assert d.audit_channel_id == 647966639266201620
    assert d.commentary_channel_id == 947095820673638400
    assert d.scheduling_needs_channel_id == 434560353461075969
    assert d.scheduling_needs_tracker is True and d.create_scheduled_events is True
    assert d.announce_channel_id == 407803705375850506
    assert d.room_open_time == 60
    assert d.helper_role_ids == [
        334797023054397450, 435200206552694794, 482353483853332481,
        426487540829388805, 613394561594687499, 334796844750209024,
    ]


# --- room-creation gate ---

async def test_before_update_data_requires_live_race(monkeypatch):
    # the live-race gate runs BEFORE update_data (no SpeedGaming/get_team I/O when absent)
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id", AsyncMock(return_value=None))
    assert await _orch().before_update_data() is False

    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id", AsyncMock(return_value=_LiveRace()))
    assert await _orch().before_update_data() is True


# --- announcement ---

async def test_send_player_room_info_announces_with_room_lock_label():
    presenter = AsyncMock()
    orch = _orch(presenter=presenter)
    await orch.send_player_room_info()
    kw = presenter.send_race_announcement.await_args.kwargs
    assert kw["series"] == "ALTTPR Main Tournament Live Qualifier"
    assert kw["seed_label"] == "Seed Distributed and Room Lock"
    assert kw["seed_time"] is not None


# --- process_race guard ladder ---

@pytest.mark.parametrize("live_race_factory,expected_msg", [
    (lambda: None, "No live race found"),
    (lambda: _LiveRace(permalink=object()), "Seed has already been generated"),
    (lambda: _LiveRace(permalink=None, pool=None), "No pool has been set"),
])
async def test_process_race_guards(monkeypatch, live_race_factory, expected_msg):
    racetime = AsyncMock()
    orch = _orch(racetime=racetime)
    _patch_update_data(orch, monkeypatch)
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id_with_relations",
                        AsyncMock(return_value=live_race_factory()))

    assert await orch.process_race(None, {"user": {"id": "rt1"}}) is False
    assert any(expected_msg in c.args[1] for c in racetime.send_message.await_args_list)


async def test_process_race_unauthorized(monkeypatch):
    racetime = AsyncMock()
    orch = _orch(racetime=racetime, authz=AsyncMock(return_value=False))
    _patch_update_data(orch, monkeypatch)
    live = _LiveRace(permalink=None, pool=_Pool(), tournament=_Tournament())
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id_with_relations", AsyncMock(return_value=live))
    monkeypatch.setattr(quals_mod.UserRepository, "get_by_rtgg_id", AsyncMock(return_value=None))

    assert await orch.process_race(None, {"user": {"id": "rt1"}}) is False
    assert any("Only a mod or admin" in c.args[1] for c in racetime.send_message.await_args_list)
    racetime.set_invitational.assert_not_awaited()  # never locked the room


async def test_process_race_no_preset(monkeypatch):
    racetime = AsyncMock()
    orch = _orch(racetime=racetime)
    _patch_update_data(orch, monkeypatch)
    live = _LiveRace(permalink=None, pool=_Pool(preset=None), tournament=_Tournament())
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id_with_relations", AsyncMock(return_value=live))
    monkeypatch.setattr(quals_mod.UserRepository, "get_by_rtgg_id", AsyncMock(return_value=object()))

    assert await orch.process_race(None, {"user": {"id": "rt1"}}) is False
    assert any("No preset has been set" in c.args[1] for c in racetime.send_message.await_args_list)


async def test_process_race_happy_path(monkeypatch):
    racetime = AsyncMock()
    racetime.get_entrants = AsyncMock(return_value=[])  # no eligible entrants for simplicity
    presenter = AsyncMock()
    orch = _orch(racetime=racetime, presenter=presenter)
    _patch_update_data(orch, monkeypatch)

    live = _LiveRace(permalink=None, pool=_Pool("mypreset"), tournament=_Tournament())
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id_with_relations", AsyncMock(return_value=live))
    monkeypatch.setattr(quals_mod.UserRepository, "get_by_rtgg_id", AsyncMock(return_value=object()))
    monkeypatch.setattr(quals_mod.triforce_text, "generate_with_triforce_text", AsyncMock(return_value=_Seed()))
    permalink_upsert = AsyncMock()
    monkeypatch.setattr(quals_mod.TournamentResultsRepository, "create_or_update_with_permalink", permalink_upsert)
    create_permalink = AsyncMock(return_value="PERMALINK")
    monkeypatch.setattr(quals_mod.AsyncTournamentRepository, "create_live_permalink", create_permalink)
    set_slug = AsyncMock()
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "set_permalink_and_slug", set_slug)

    rolled = await orch.process_race(None, {"user": {"id": "rt1"}})

    assert rolled is True
    # locked the room before rolling
    racetime.set_invitational.assert_awaited_once_with("alttpr/quals")
    # raceinfo + seed message carry url + file-select code
    racetime.set_bot_raceinfo.assert_awaited_once_with("alttpr/quals", "http://alttpr/seed - (Bow/Boots/Bombs)")
    assert any(c.args == ("alttpr/quals", "Seed: http://alttpr/seed - (Bow/Boots/Bombs)") for c in racetime.send_message.await_args_list)
    # TournamentResults + AsyncTournamentPermalink persistence
    assert permalink_upsert.await_args.kwargs["permalink"] == "http://alttpr/seed"
    create_permalink.assert_awaited_once()
    assert create_permalink.await_args.kwargs["url"] == "http://alttpr/seed"
    assert "(Bow/Boots/Bombs)" in create_permalink.await_args.kwargs["notes"]
    set_slug.assert_awaited_once_with(live, "PERMALINK", "alttpr/quals")
    # audit messages use the room url; note the legacy " -Eligible" (no space) is preserved
    assert any("-Eligible entrants for this pool:" in (c.args[0] if c.args else "") for c in presenter.send_audit_message.await_args_list)


# --- eligible-entrant writes ---

async def test_write_eligible_skips_run_limit_and_active(monkeypatch):
    racetime = AsyncMock()
    racetime.get_entrants = AsyncMock(return_value=[
        {"id": "rtA", "name": "A", "twitch_name": "tA"},
        {"id": "rtB", "name": "B", "twitch_name": "tB"},
        {"id": "rtC", "name": "C", "twitch_name": "tC"},
    ])
    orch = _orch(racetime=racetime)

    users = {"rtA": _named("A"), "rtB": _named("B"), "rtC": _named("C")}
    monkeypatch.setattr(quals_mod.UserRepository, "get_or_create_by_rtgg_id",
                        AsyncMock(side_effect=lambda rtgg_id, defaults: (users[rtgg_id], True)))
    monkeypatch.setattr(quals_mod.UserRepository, "set_twitch_name", AsyncMock())
    # A is over the run limit; B has an active race; C is eligible
    monkeypatch.setattr(quals_mod.AsyncTournamentRepository, "count_completed_pool_races",
                        AsyncMock(side_effect=lambda t, u, p: 5 if u.display_name == "A" else 0))
    monkeypatch.setattr(quals_mod.AsyncTournamentRepository, "user_has_active_race",
                        AsyncMock(side_effect=lambda t, u: u.display_name == "B"))
    create_entry = AsyncMock()
    monkeypatch.setattr(quals_mod.AsyncTournamentRepository, "create_pending_live_entry", create_entry)

    live = _LiveRace(pool=_Pool(), tournament=_Tournament())
    eligible = await orch._write_eligible_entrants(live, "PERMALINK")

    assert eligible == ["C"]  # only C
    create_entry.assert_awaited_once()


# --- race start ---

async def test_on_race_start_promotes_and_announces(monkeypatch):
    racetime = AsyncMock()
    racetime.get_entrant_ids = AsyncMock(return_value=["rtA", "rtB"])
    racetime.get_started_at = AsyncMock(return_value="2026-06-26T22:00:00+00:00")
    presenter = AsyncMock()
    orch = _orch(racetime=racetime, presenter=presenter)

    live = _LiveRace()
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "get_by_episode_id", AsyncMock(return_value=live))
    process_start = AsyncMock(return_value=["A", "B"])
    monkeypatch.setattr(quals_mod.AsyncTournamentLiveRaceRepository, "process_race_start", process_start)

    await orch.on_race_start()

    # parsed start time passed through to the repo
    args = process_start.await_args.args
    assert args[0] is live and args[1] == ["rtA", "rtB"]
    assert any("Final eligible entrants for this pool: A, B" in c.args[1] for c in racetime.send_message.await_args_list)
    assert any("Good luck, have fun!" in c.args[1] for c in racetime.send_message.await_args_list)
    assert any("Entrants: A, B" in (c.args[0] if c.args else "") for c in presenter.send_audit_message.await_args_list)


def _named(name):
    u = type("U", (), {})()
    u.display_name = name
    return u
