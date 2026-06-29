"""Unit tests for the SMRL playoffs orchestrator (PR6).

Covers the custom SM seed roll (VARIA / DASH), the settings-submission form mapping +
persistence, the submission reminder, the room-creation submission gate, the welcome, and
the definition transcription. Presenter / racetime / repositories are mocked.
"""

from unittest.mock import AsyncMock

import pytest

import alttprbot.services.tournament.smrl as smrl_mod
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.smrl import (
    SMRL_DEFINITION,
    SMRL_SUBMISSION_FORM,
    SMRLPlayoffsOrchestrator,
)
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer

EPISODE = {
    "id": 100,
    "event": {"shortName": "SMRL", "slug": "smrl"},
    "match1": {"title": "Round 1", "players": []},
    "channels": [],
    "whenCountdown": "2026-06-26T18:00:00-04:00",
    "when": "2026-06-26T18:30:00-04:00",
}


def _orch(*, presenter=None, racetime=None):
    orch = SMRLPlayoffsOrchestrator(
        SMRL_DEFINITION, 100,
        presenter=presenter or AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=racetime or AsyncMock(),
    )
    orch.episode = EPISODE
    orch.players = [TournamentPlayer("rt1", "A", 1), TournamentPlayer("rt2", "B", 2)]
    return orch


class _Game:
    def __init__(self, settings):
        self.settings = settings


def _prepare_process_race(orch, monkeypatch, settings):
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.speedgaming, "get_episode", AsyncMock(return_value=EPISODE))
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=_Game(settings)))
    orch.racetime.get_team = AsyncMock(return_value={"members": []})
    orch.room = RaceRoom(name="smr/room", url="http://rt/smr/room", entrant_ids=[])
    permalink_upsert = AsyncMock()
    monkeypatch.setattr(smrl_mod.TournamentResultsRepository, "create_or_update_with_permalink", permalink_upsert)
    return permalink_upsert


# --- process_race: SM seed generation ---

async def test_process_race_smvaria(monkeypatch):
    racetime = AsyncMock()
    orch = _orch(racetime=racetime)
    permalink_upsert = _prepare_process_race(orch, monkeypatch, {"randomizer": "smvaria", "preset": "RLS4W5"})

    seed = type("S", (), {"url": "http://varia/seed"})()
    monkeypatch.setattr(smrl_mod.SuperMetroidVaria, "create", AsyncMock(return_value=seed))

    rolled = await orch.process_race(None, None)

    assert rolled is True
    smrl_mod.SuperMetroidVaria.create.assert_awaited_once_with(
        settings_preset="RLS4W5", skills_preset="Season_Races", race=True
    )
    racetime.send_message.assert_any_await("smr/room", "http://varia/seed")
    racetime.set_bot_raceinfo.assert_awaited_once_with("smr/room", "http://varia/seed")
    assert racetime.send_message.await_args_list[-1].args == ("smr/room", "Seed has been generated!")
    assert permalink_upsert.await_args.kwargs["permalink"] == "http://varia/seed"
    assert permalink_upsert.await_args.kwargs["srl_id"] == "smr/room"


async def test_process_race_smdash(monkeypatch):
    racetime = AsyncMock()
    orch = _orch(racetime=racetime)
    permalink_upsert = _prepare_process_race(orch, monkeypatch, {"randomizer": "smdash", "preset": "classic_mm"})

    monkeypatch.setattr(smrl_mod.smdash, "create_smdash", AsyncMock(return_value="http://dash/seed"))

    await orch.process_race(None, None)

    smrl_mod.smdash.create_smdash.assert_awaited_once_with(mode="classic_mm")
    racetime.send_message.assert_any_await("smr/room", "http://dash/seed")
    racetime.set_bot_raceinfo.assert_awaited_once_with("smr/room", "http://dash/seed")
    assert permalink_upsert.await_args.kwargs["permalink"] == "http://dash/seed"


# --- process_submission_form: game-number -> randomizer/preset mapping ---

@pytest.mark.parametrize("payload,expected", [
    ({"game": "1"}, ("smvaria", "RLS4W5")),
    ({"game": "2"}, ("smdash", "recall_mm")),
    ({"game": "3"}, ("smvaria", "RLS4GS")),
    ({"game": "4", "preset": "classic_mm"}, ("smdash", "classic_mm")),
    ({"game": "4", "preset": "RLS4P2"}, ("smvaria", "RLS4P2")),
    ({"game": "5", "preset": "RLS4W3"}, ("smvaria", "RLS4W3")),
])
async def test_process_submission_form_mapping(monkeypatch, payload, expected):
    presenter = AsyncMock()
    orch = _orch(presenter=presenter)
    upsert = AsyncMock()
    monkeypatch.setattr(smrl_mod.TournamentGamesRepository, "upsert_by_episode_id", upsert)

    await orch.process_submission_form(payload, submitted_by="someuser")

    randomizer, preset = expected
    persisted = upsert.await_args.kwargs["defaults"]
    assert persisted["settings"] == {"randomizer": randomizer, "preset": preset}
    assert persisted["event"] == "smrl"
    assert persisted["game_number"] == int(payload["game"])
    assert upsert.await_args.kwargs["episode_id"] == 100

    conf = presenter.send_submission_confirmation.await_args.kwargs
    assert conf["randomizer"] == randomizer and conf["preset"] == preset
    assert conf["submitted_by"] == "someuser"
    assert conf["game_number"] == int(payload["game"])
    assert conf["players"] == [("A", 1), ("B", 2)]


# --- send_race_submission_form: reminders + mark submitted ---

async def test_send_race_submission_form_reminds_and_marks(monkeypatch):
    presenter = AsyncMock()
    orch = _orch(presenter=presenter)
    orch.tournament_game = None  # not yet submitted
    upsert = AsyncMock()
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "upsert_by_episode_id", upsert)

    await orch.send_race_submission_form(warning=False)

    presenter.send_player_reminders.assert_awaited_once()
    ids, msg = presenter.send_player_reminders.await_args.args
    assert ids == [1, 2]
    assert "Do not forget to submit settings" in msg
    assert upsert.await_args.kwargs["defaults"] == {"event": "smrl", "submitted": 1}


async def test_send_race_submission_form_warning_message(monkeypatch):
    presenter = AsyncMock()
    orch = _orch(presenter=presenter)
    orch.tournament_game = None
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "upsert_by_episode_id", AsyncMock())

    await orch.send_race_submission_form(warning=True)

    _, msg = presenter.send_player_reminders.await_args.args
    assert "cannot be created because settings have not submitted" in msg


async def test_send_race_submission_form_skips_when_already_submitted():
    presenter = AsyncMock()
    orch = _orch(presenter=presenter)
    orch.tournament_game = type("G", (), {"submitted": 1})()
    await orch.send_race_submission_form(warning=False)
    presenter.send_player_reminders.assert_not_awaited()  # already submitted, not a warning


# --- before_room_creation: submission gate ---

async def test_before_room_creation_gated_when_no_settings(monkeypatch):
    orch = _orch()
    orch.tournament_game = None
    orch.send_race_submission_form = AsyncMock()

    proceed = await orch.before_room_creation()

    assert proceed is False
    orch.send_race_submission_form.assert_awaited_once_with(warning=True)


async def test_before_room_creation_allows_when_settings_present():
    orch = _orch()
    orch.tournament_game = type("G", (), {"settings": {"randomizer": "smvaria", "preset": "RLS4W5"}})()
    assert await orch.before_room_creation() is True


# --- welcome: single pinned action ---

async def test_send_room_welcome_single_pinned_action():
    racetime = AsyncMock()
    orch = _orch(racetime=racetime)
    orch.room = RaceRoom(name="smr/room", url="http://rt/smr/room", entrant_ids=[])

    await orch.send_room_welcome()

    racetime.send_pinned_action.assert_awaited_once()
    pinned = racetime.send_pinned_action.await_args
    assert pinned.args[0] == "smr/room"
    assert "Use !tournamentrace" in pinned.args[1]
    assert pinned.kwargs["label"] == "Roll Tournament Seed"
    assert pinned.kwargs["message"] == "!tournamentrace"
    racetime.send_message.assert_not_awaited()  # welcome is one combined pinned message


# --- definition + base + submission form ---

def test_smrl_is_base_orchestrator():
    assert SMRLPlayoffsOrchestrator.__mro__[1] is TournamentOrchestrator


def test_smrl_definition_and_form():
    d = SMRL_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal) == ("smrl", "smr", "Beat the game")
    assert d.guild_id == 500362417629560881
    assert d.audit_channel_id == 1080994224880750682
    assert d.helper_role_ids == [500363025958567948, 501810831504179250, 504725352745140224]
    assert d.commentary_channel_id is None
    # the submission form lives on the definition (consumed by the JSON API + cog)
    assert d.submission_form is SMRL_SUBMISSION_FORM
    assert [s["key"] for s in SMRL_SUBMISSION_FORM] == ["game", "preset"]
    assert SMRL_SUBMISSION_FORM[0]["settings"]["1"] == "Power"
    assert SMRL_SUBMISSION_FORM[1]["settings"]["classic_mm"] == "Classic DASH"
