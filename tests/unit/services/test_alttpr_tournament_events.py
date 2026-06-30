"""Unit tests for the PR4 ALTTPR-tail event orchestrators + their definitions.

Covers the title-map roll (success + the legacy KeyError "Invalid mode" path), the
fixed-preset rolls (nologic / hmg), the smwde base-orchestrator wiring, and the
hardcoded-ID transcription for every definition (the main migration risk).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import alttprbot.services.tournament.alttpr as alttpr_mod
import alttprbot.services.tournament.nologic as nologic_mod
import alttprbot.services.tournament.alttprhmg as hmg_mod
from alttprbot.services.tournament import SeedResult
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.alttprde import (
    ALTTPRDE_DEFINITION,
    ALTTPRDE_TITLE_MAP,
    ALTTPRDEOrchestrator,
)
from alttprbot.services.tournament.alttprmini import (
    ALTTPRMINI_DEFINITION,
    ALTTPRMINI_TITLE_MAP,
    ALTTPRMiniOrchestrator,
)
from alttprbot.services.tournament.alttprhmg import ALTTPRHMG_DEFINITION, ALTTPRHMGOrchestrator
from alttprbot.services.tournament.nologic import NOLOGIC_DEFINITION, NoLogicOrchestrator
from alttprbot.services.tournament.smwde import SMWDE_DEFINITION, SMWDEOrchestrator
from alttprbot.services.tournament.types import RaceRoom


class _FakeSeed:
    code = ["Bow", "Boots"]
    url = "http://seed/permalink"


def _event_orch(cls, definition, *, racetime=None, episode_title="Round 1: Open"):
    orch = cls(
        definition, 100,
        presenter=AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=racetime or AsyncMock(),
    )
    orch.episode = {"match1": {"title": episode_title}}
    orch.room = RaceRoom(name="alttpr/room", url="http://rt/room", entrant_ids=[])
    return orch


def _patch_preset(monkeypatch, module):
    preset_cls = MagicMock()
    preset_cls.return_value.generate = AsyncMock(return_value=_FakeSeed())
    monkeypatch.setattr(module.generator, "ALTTPRPreset", preset_cls)
    return preset_cls


# --- title-map roll (de / mini) ---

async def test_de_roll_selects_preset_from_title(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, alttpr_mod)  # helper lives in alttpr.py
    orch = _event_orch(ALTTPRDEOrchestrator, ALTTPRDE_DEFINITION, episode_title="DE Finale: 6/6 Fast Ganon")
    result = await orch.roll()
    assert isinstance(result, SeedResult)
    preset_cls.assert_called_once_with("open_fast_66")  # mapped from "6/6 Fast Ganon"
    preset_cls.return_value.generate.assert_awaited_once_with(hints=False, spoilers="off", allow_quickswap=True)


async def test_mini_roll_selects_preset_from_title(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, alttpr_mod)
    orch = _event_orch(ALTTPRMiniOrchestrator, ALTTPRMINI_DEFINITION, episode_title="All Dungeons")
    await orch.roll()
    preset_cls.assert_called_once_with("adboots")
    preset_cls.return_value.generate.assert_awaited_once_with(hints=False, spoilers="off", allow_quickswap=True)


async def test_title_map_roll_handles_title_without_colon(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, alttpr_mod)
    # no colon -> the whole title (stripped) is the key
    orch = _event_orch(ALTTPRDEOrchestrator, ALTTPRDE_DEFINITION, episode_title="Standard")
    await orch.roll()
    preset_cls.assert_called_once_with("standard")


async def test_title_map_roll_invalid_mode_messages_and_raises(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, alttpr_mod)
    racetime = AsyncMock()
    orch = _event_orch(ALTTPRDEOrchestrator, ALTTPRDE_DEFINITION, racetime=racetime, episode_title="Bracket: Totally Unknown Mode")
    with pytest.raises(KeyError):
        await orch.roll()
    racetime.send_message.assert_awaited_once_with(
        "alttpr/room", "Invalid mode chosen, please contact a tournament admin for assistance."
    )
    preset_cls.return_value.generate.assert_not_awaited()  # no seed generated on bad title


# --- fixed-preset rolls (nologic / hmg) ---

async def test_nologic_roll_fixed_preset(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, nologic_mod)
    orch = _event_orch(NoLogicOrchestrator, NOLOGIC_DEFINITION)
    await orch.roll()
    preset_cls.assert_called_once_with("nologic_rods")
    preset_cls.return_value.generate.assert_awaited_once_with(allow_quickswap=True, branch="beeta")


async def test_hmg_roll_fixed_preset(monkeypatch):
    preset_cls = _patch_preset(monkeypatch, hmg_mod)
    orch = _event_orch(ALTTPRHMGOrchestrator, ALTTPRHMG_DEFINITION)
    await orch.roll()
    preset_cls.assert_called_once_with("hmg")
    preset_cls.return_value.generate.assert_awaited_once_with(
        allow_quickswap=True, tournament=True, hints=False, spoilers="off", branch="live"
    )


# --- smwde is a pure base-orchestrator event (no seed roll) ---

def test_smwde_extends_base_orchestrator_not_alttpr():
    assert issubclass(SMWDEOrchestrator, TournamentOrchestrator)
    assert not issubclass(SMWDEOrchestrator, ALTTPRTournamentOrchestrator)


async def test_smwde_process_race_is_noop():
    orch = _event_orch(SMWDEOrchestrator, SMWDE_DEFINITION)
    assert await orch.process_race(None, None) is False  # base no-op -> seed_rolled never set


# --- definition ID transcription guards (one assert block per event) ---

def test_smwde_definition():
    d = SMWDE_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal, d.lang) == ("smwde", "smw-hacks", "Any%", "de")
    assert d.guild_id == 753727862229565612
    assert d.audit_channel_id == 826775494329499648
    assert d.scheduling_needs_channel_id == 835946387065012275
    assert d.helper_role_ids == [754845429773893782, 753742980820631562]
    assert d.commentary_channel_id is None


def test_nologic_definition():
    d = NOLOGIC_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal, d.lang) == ("nologic", "alttpr", "Beat the game (glitched)", "en")
    assert d.guild_id == 535946014037901333
    assert d.audit_channel_id == 850226062864023583
    assert d.commentary_channel_id == 549709098015391764
    assert d.helper_role_ids == []  # legacy nologic set no helper roles


def test_hmg_definition():
    d = ALTTPRHMG_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal) == ("alttprhmg", "alttpr", "Beat the game (glitched)")
    assert d.lang == "en"  # legacy didn't set lang -> default
    assert d.guild_id == 535946014037901333
    assert d.audit_channel_id == 850226062864023583
    assert d.commentary_channel_id == 549709098015391764
    assert d.helper_role_ids == [549709214000480276, 535962854004883467, 535962802230132737]


def test_de_definition():
    d = ALTTPRDE_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal, d.lang) == ("alttprde", "alttpr", "Beat the game", "de")
    assert d.guild_id == 469300113290821632
    assert d.audit_channel_id == 473668481011679234
    assert d.commentary_channel_id == 469317757331308555
    assert d.helper_role_ids == [534030648713674765, 469300493542490112, 623071415129866240]
    assert d.stream_delay == 10
    assert d.create_scheduled_events is True


def test_mini_definition():
    d = ALTTPRMINI_DEFINITION
    assert (d.event_slug, d.racetime_category, d.racetime_goal, d.lang) == ("alttprmini", "alttpr", "Beat the game", "de")
    assert d.guild_id == 469300113290821632
    assert d.audit_channel_id == 473668481011679234
    assert d.commentary_channel_id == 469317757331308555
    assert d.helper_role_ids == [534030648713674765, 469300493542490112, 623071415129866240]
    assert d.coop is False
    assert d.stream_delay == 0  # legacy mini left stream_delay commented out -> default


def test_de_and_mini_title_maps_match_legacy():
    assert ALTTPRDE_TITLE_MAP["Open"] == "open"
    assert ALTTPRDE_TITLE_MAP["Standard Swordless"] == "nightcl4w/german_swordless2024"
    assert ALTTPRDE_TITLE_MAP["All Dungeons Keysanity"] == "adkeys_boots"
    assert len(ALTTPRDE_TITLE_MAP) == 12
    assert ALTTPRMINI_TITLE_MAP["6/6 Defeat Ganon"] == "nightcl4w/6_6_defeat_ganon"
    assert ALTTPRMINI_TITLE_MAP["Casual Boots"] == "casualboots"
    assert len(ALTTPRMINI_TITLE_MAP) == 5
