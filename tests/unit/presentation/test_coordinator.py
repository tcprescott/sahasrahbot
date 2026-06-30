"""Tests for the TournamentCoordinator (cog-facing surface + lifecycle delegation).

The discord cog reads live discord objects + scalar props off the dispatched coordinator;
the coordinator resolves the TournamentDefinition into a live TournamentConfig and exposes
the legacy property surface. The RaceTime handler drives the lifecycle methods. Here we
drive _build_config, the properties, the room-refresh/seed_rolled logic, and the
construction gates with a fake discordbot. (Replaces the old OrchestratorAdapter tests.)
"""

from unittest.mock import AsyncMock

import pytest

import alttprbot.presentation.discord.tournament.coordinator as coord_mod
from alttprbot.presentation.discord.tournament.coordinator import TournamentCoordinator
from alttprbot.services.tournament import TournamentDefinition
from alttprbot.services.tournament.registry import TournamentEntry


class _Role:
    def __init__(self, rid):
        self.id = rid


class _Guild:
    def __init__(self, roles):
        self._roles = {r: _Role(r) for r in roles}

    def get_role(self, rid):
        return self._roles.get(rid)


class _FakeBot:
    def __init__(self, guild, channels):
        self._guild = guild
        self._channels = channels

    def get_guild(self, gid):
        return self._guild if gid == 555 else None

    def get_channel(self, cid):
        return self._channels.get(cid)

    async def wait_until_ready(self):
        return None


DEFN = TournamentDefinition(
    event_slug="test", racetime_category="test", racetime_goal="Beat the game",
    guild_id=555, audit_channel_id=10, commentary_channel_id=11,
    scheduling_needs_channel_id=None, helper_role_ids=[7, 8, 999],
    stream_delay=10, room_open_time=35, lang="en", submission_form="myform",
    create_scheduled_events=True, scheduling_needs_tracker=True,
)


def _entry(orchestrator_cls):
    return TournamentEntry(orchestrator_cls, DEFN)


def _patch_bot(monkeypatch):
    guild = _Guild(roles=[7, 8])  # 999 is not a real role -> dropped
    bot = _FakeBot(guild, channels={10: "AUDIT", 11: "COMMENTARY"})
    monkeypatch.setattr(coord_mod, "discordbot", bot)
    return guild


def test_build_config_resolves_ids_to_live_objects(monkeypatch):
    guild = _patch_bot(monkeypatch)
    coord = TournamentCoordinator(_entry(object))
    cfg = coord._build_config()

    assert cfg.guild is guild
    assert cfg.audit_channel == "AUDIT"
    assert cfg.commentary_channel == "COMMENTARY"
    assert cfg.scheduling_needs_channel is None  # id was None
    assert [r.id for r in cfg.helper_roles] == [7, 8]  # unknown role 999 dropped
    assert cfg.racetime_category == "test"
    assert cfg.create_scheduled_events is True
    assert cfg.scheduling_needs_tracker is True


def test_cog_facing_properties(monkeypatch):
    _patch_bot(monkeypatch)
    coord = TournamentCoordinator(_entry(object))
    coord.data = coord._build_config()

    assert coord.guild is not None
    assert coord.audit_channel == "AUDIT"
    assert coord.commentary_channel == "COMMENTARY"
    assert coord.lang == "en"
    assert coord.submission_form == "myform"
    assert coord.hours_before_room_open == (10 + 35) / 60
    # the cog reads .data.racetime_category / .data.scheduling_needs_channel
    assert coord.data.racetime_category == "test"
    assert coord.data.scheduling_needs_channel is None


def test_player_racetime_ids_safe_without_orchestrator(monkeypatch):
    _patch_bot(monkeypatch)
    coord = TournamentCoordinator(_entry(object))
    assert coord.player_racetime_ids == []  # orchestrator not built yet


def _fake_handler(seed_rolled=False):
    handler = type("H", (), {})()
    handler.data = {"url": "/r", "name": "test/clever-cat", "entrants": [{"user": {"id": "e1"}}]}
    handler.seed_rolled = seed_rolled
    return handler


def _coord_with_orch(monkeypatch, process_race):
    _patch_bot(monkeypatch)
    fake_gw = type("GW", (), {"http_uri": lambda self, cat, url: f"http://rt{url}"})()
    monkeypatch.setattr(coord_mod.racetime_gateway, "get", lambda: fake_gw)

    coord = TournamentCoordinator(_entry(object))
    coord.rtgg_handler = _fake_handler()
    orch = AsyncMock()
    orch.process_race = process_race
    coord.orchestrator = orch
    return coord, orch


async def test_process_tournament_race_refreshes_room_and_sets_seed_rolled(monkeypatch):
    coord, orch = _coord_with_orch(monkeypatch, AsyncMock(return_value=True))

    await coord.process_tournament_race(None, None)

    # room refreshed from the live handler (fresh entrants/url) before delegating
    assert orch.room.name == "test/clever-cat"
    assert orch.room.entrant_ids == ["e1"]
    assert orch.room.url == "http://rt/r"
    orch.process_race.assert_awaited_once()
    assert coord.rtgg_handler.seed_rolled is True


async def test_process_tournament_race_no_seed_rolled_when_handler_does_not_roll(monkeypatch):
    coord, _ = _coord_with_orch(monkeypatch, AsyncMock(return_value=False))
    await coord.process_tournament_race(None, None)
    assert coord.rtgg_handler.seed_rolled is False  # falsy return -> guard untouched


async def test_process_tournament_race_leaves_room_rerollable_on_error(monkeypatch):
    coord, _ = _coord_with_orch(monkeypatch, AsyncMock(side_effect=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        await coord.process_tournament_race(None, None)
    assert coord.rtgg_handler.seed_rolled is False  # exception -> not set


# --- submission-flow delegation ---

async def test_coordinator_delegates_process_submission_form(monkeypatch):
    coord, orch = _coord_with_orch(monkeypatch, AsyncMock())
    orch.process_submission_form = AsyncMock(return_value=None)
    await coord.process_submission_form({"game": "1"}, submitted_by="u")
    orch.process_submission_form.assert_awaited_once_with({"game": "1"}, "u")


async def test_coordinator_delegates_send_race_submission_form(monkeypatch):
    coord, orch = _coord_with_orch(monkeypatch, AsyncMock())
    orch.send_race_submission_form = AsyncMock()
    await coord.send_race_submission_form(warning=True)
    orch.send_race_submission_form.assert_awaited_once_with(warning=True)


async def test_coordinator_versus_delegates_to_orchestrator(monkeypatch):
    coord, orch = _coord_with_orch(monkeypatch, AsyncMock())
    orch.versus = "A vs. B"
    assert coord.versus == "A vs. B"


def test_coordinator_versus_safe_without_orchestrator(monkeypatch):
    _patch_bot(monkeypatch)
    coord = TournamentCoordinator(_entry(object))
    assert coord.versus is None


class _GatedOrchestrator:
    """Minimal orchestrator that refuses room creation after update_data (smrl-style gate)."""

    def __init__(self, *args, **kwargs):
        self.updated = False

    async def before_update_data(self):
        return True

    async def update_data(self):
        self.updated = True

    async def before_room_creation(self):
        return False


class _PreGatedOrchestrator(_GatedOrchestrator):
    """Refuses room creation BEFORE update_data (alttpr_quals live-race-style gate)."""

    update_data_calls = 0

    async def before_update_data(self):
        return False

    async def update_data(self):
        type(self).update_data_calls += 1


async def test_construct_race_room_aborts_when_gated(monkeypatch):
    _patch_bot(monkeypatch)
    started = AsyncMock()
    fake_gw = type("GW", (), {"start_race": started})()
    monkeypatch.setattr(coord_mod.racetime_gateway, "get", lambda: fake_gw)

    handler = await TournamentCoordinator.construct_race_room(_entry(_GatedOrchestrator), 123)

    assert handler is None  # gated -> no room
    started.assert_not_awaited()  # start_race never reached


async def test_construct_race_room_pre_io_gate_skips_update_data(monkeypatch):
    _patch_bot(monkeypatch)
    started = AsyncMock()
    fake_gw = type("GW", (), {"start_race": started})()
    monkeypatch.setattr(coord_mod.racetime_gateway, "get", lambda: fake_gw)

    _PreGatedOrchestrator.update_data_calls = 0
    handler = await TournamentCoordinator.construct_race_room(_entry(_PreGatedOrchestrator), 123)

    assert handler is None
    started.assert_not_awaited()
    # the pre-I/O gate short-circuits before update_data runs any SpeedGaming/RaceTime I/O
    assert _PreGatedOrchestrator.update_data_calls == 0
