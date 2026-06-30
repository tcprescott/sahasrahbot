"""Unit tests for the ALTTPR-family seed-rolling orchestrator + the Boots event.

Mock the presenter / racetime gateway / player resolver / repositories; assert the
``process_race`` flow matches the legacy ``ALTTPRTournamentRace.process_tournament_race``
ordering and the cross-gateway DM-failure fallback.
"""

from unittest.mock import AsyncMock, call

import pytest

from alttprbot.services.tournament import SeedResult, TournamentDefinition
from alttprbot.services.tournament.alttpr import ALTTPRTournamentOrchestrator
from alttprbot.services.tournament.boots import BOOTS_DEFINITION, BootsOrchestrator
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer

EPISODE = {
    "id": 100,
    "event": {"shortName": "TestEvent", "slug": "boots"},
    "match1": {
        "title": "Round 1",
        "players": [
            {"discordId": "1", "discordTag": "a", "displayName": "A", "publicStream": "yes", "streamingFrom": "tA"},
            {"discordId": "2", "discordTag": "b", "displayName": "B", "publicStream": "yes", "streamingFrom": "tB"},
        ],
    },
    "channels": [{"name": "restreamA"}, {"name": "has space"}],
    "whenCountdown": "2026-06-26T18:00:00-04:00",
    "when": "2026-06-26T18:30:00-04:00",
}


class _FakeSeed:
    code = ["Bow", "Boots"]
    url = "http://seed/permalink"


async def _player_resolver(player):
    return TournamentPlayer(
        rtgg_id=f"rt{player['discordId']}",
        name=player["displayName"],
        discord_user_id=int(player["discordId"]),
    )


class _RollingOrchestrator(ALTTPRTournamentOrchestrator):
    """Concrete ALTTPR orchestrator whose roll() returns a fixed seed (no generator)."""

    async def roll(self):
        return SeedResult(seed=_FakeSeed())


def _definition(**kw):
    base = dict(event_slug="boots", racetime_category="alttpr", racetime_goal="Beat the game - Tournament (Solo)")
    base.update(kw)
    return TournamentDefinition(**base)


def _orchestrator(cls=_RollingOrchestrator, definition=None, *, presenter, racetime):
    return cls(
        definition or _definition(),
        100,
        presenter=presenter,
        player_resolver=_player_resolver,
        gatekeep_checker=AsyncMock(return_value=False),
        racetime=racetime,
    )


def _prepare(orch, monkeypatch, *, entrant_ids):
    """Stub out update_data's external calls and set the live room."""
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.speedgaming, "get_episode", AsyncMock(return_value=EPISODE))
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=None))
    orch.room = RaceRoom(name="alttpr/clever-cat", url="http://rt/alttpr/clever-cat", entrant_ids=entrant_ids)


async def test_process_race_full_flow(monkeypatch):
    presenter = AsyncMock()
    presenter.build_race_embeds = AsyncMock(return_value=("EMBED", "TOURNEMBED"))
    presenter.send_player_seed_dm = AsyncMock(return_value=True)
    racetime = AsyncMock()
    racetime.get_team = AsyncMock(return_value={"members": []})
    racetime.get_entrant_ids = AsyncMock(return_value=["e1", "e2"])

    orch = _orchestrator(presenter=presenter, racetime=racetime)
    _prepare(orch, monkeypatch, entrant_ids=["e1", "e2"])

    import alttprbot.services.tournament.alttpr as alttpr_mod
    permalink_upsert = AsyncMock()
    monkeypatch.setattr(alttpr_mod.TournamentResultsRepository, "create_or_update_with_permalink", permalink_upsert)

    rolled = await orch.process_race(None, None)

    assert rolled is True

    # 1) announce, 2) (per-entrant url dm x2), 3) final completion message — all via racetime.send_message
    msgs = [c for c in racetime.send_message.await_args_list]
    assert msgs[0] == call("alttpr/clever-cat", "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
    # per-entrant seed url DMs — entrants read fresh from the gateway (post-roll), not
    # from the construction-time room snapshot
    racetime.get_entrant_ids.assert_awaited_once_with("alttpr/clever-cat")
    assert call("alttpr/clever-cat", "http://seed/permalink", direct_to="e1") in msgs
    assert call("alttpr/clever-cat", "http://seed/permalink", direct_to="e2") in msgs
    # completion message last
    assert "Seed has been generated" in msgs[-1].args[1]

    # embeds built with the live-room context
    presenter.build_race_embeds.assert_awaited_once()
    kwargs = presenter.build_race_embeds.await_args.kwargs
    assert kwargs["room_url"] == "http://rt/alttpr/clever-cat"
    assert kwargs["broadcast_channels"] == ["restreamA"]  # "has space" excluded
    assert kwargs["versus"] == "A vs. B"

    # raceinfo set from the seed hash
    racetime.set_bot_raceinfo.assert_awaited_once_with("alttpr/clever-cat", "(Bow/Boots)")

    # audit gets the public embed; commentary gets the tournament embed (broadcasts present)
    presenter.send_audit_message.assert_awaited_once_with(embed="EMBED")
    presenter.send_commentary_message.assert_awaited_once_with("TOURNEMBED", has_broadcasts=True)

    # each player DM'd the public embed
    assert presenter.send_player_seed_dm.await_count == 2
    assert all(c.kwargs["embed"] == "EMBED" for c in presenter.send_player_seed_dm.await_args_list)
    presenter.send_audit_alert.assert_not_awaited()  # all DMs succeeded

    # permalink persisted keyed on the room name
    permalink_upsert.assert_awaited_once()
    assert permalink_upsert.await_args.kwargs["srl_id"] == "alttpr/clever-cat"
    assert permalink_upsert.await_args.kwargs["permalink"] == "http://seed/permalink"
    assert permalink_upsert.await_args.kwargs["defaults"]["event"] == "boots"


async def test_process_race_dm_failure_alerts_audit_and_racetime(monkeypatch):
    presenter = AsyncMock()
    presenter.build_race_embeds = AsyncMock(return_value=("EMBED", "TOURNEMBED"))
    # first player DM succeeds, second fails -> fallback path for player "B"
    presenter.send_player_seed_dm = AsyncMock(side_effect=[True, False])
    racetime = AsyncMock()
    racetime.get_team = AsyncMock(return_value={"members": []})
    racetime.get_entrant_ids = AsyncMock(return_value=[])

    orch = _orchestrator(presenter=presenter, racetime=racetime)
    _prepare(orch, monkeypatch, entrant_ids=[])

    import alttprbot.services.tournament.alttpr as alttpr_mod
    monkeypatch.setattr(alttpr_mod.TournamentResultsRepository, "create_or_update_with_permalink", AsyncMock())

    await orch.process_race(None, None)

    presenter.send_audit_alert.assert_awaited_once_with("@here could not send DM to B")
    racetime.send_message.assert_any_await(
        "alttpr/clever-cat",
        "Could not send DM to B.  Please contact a Tournament Moderator for assistance.",
    )


async def test_process_race_no_broadcasts_skips_commentary(monkeypatch):
    presenter = AsyncMock()
    presenter.build_race_embeds = AsyncMock(return_value=("EMBED", "TOURNEMBED"))
    presenter.send_player_seed_dm = AsyncMock(return_value=True)
    racetime = AsyncMock()
    racetime.get_team = AsyncMock(return_value={"members": []})
    racetime.get_entrant_ids = AsyncMock(return_value=[])

    orch = _orchestrator(presenter=presenter, racetime=racetime)
    # episode with no valid broadcast channels
    no_bc = {**EPISODE, "channels": [{"name": "has space"}]}
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.speedgaming, "get_episode", AsyncMock(return_value=no_bc))
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=None))
    orch.room = RaceRoom(name="alttpr/r", url="http://rt/r", entrant_ids=[])
    import alttprbot.services.tournament.alttpr as alttpr_mod
    monkeypatch.setattr(alttpr_mod.TournamentResultsRepository, "create_or_update_with_permalink", AsyncMock())

    await orch.process_race(None, None)

    presenter.send_commentary_message.assert_awaited_once_with("TOURNEMBED", has_broadcasts=False)


async def test_send_room_welcome_posts_welcome_and_pinned_action():
    racetime = AsyncMock()
    orch = _orchestrator(presenter=AsyncMock(), racetime=racetime)
    orch.room = RaceRoom(name="alttpr/r", url="http://rt/r", entrant_ids=[])

    await orch.send_room_welcome()

    assert racetime.send_message.await_count == 1
    assert 'Roll Tournament Seed' in racetime.send_message.await_args.args[1]
    racetime.send_pinned_action.assert_awaited_once()
    pinned = racetime.send_pinned_action.await_args
    assert pinned.args[0] == "alttpr/r"
    assert pinned.args[1] == "Tournament Controls:"
    assert pinned.kwargs["label"] == "Roll Tournament Seed"
    assert pinned.kwargs["message"] == "!tournamentrace"


async def test_base_roll_must_be_overridden():
    orch = ALTTPRTournamentOrchestrator(
        _definition(), 1, presenter=AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=AsyncMock(),
    )
    with pytest.raises(NotImplementedError):
        await orch.roll()


async def test_boots_roll_generates_casualboots(monkeypatch):
    import alttprbot.services.tournament.boots as boots_mod
    seed = _FakeSeed()
    preset = type("P", (), {"generate": AsyncMock(return_value=seed)})()
    preset_ctor = AsyncMock()  # not awaited; ALTTPRPreset(...) is a sync constructor
    monkeypatch.setattr(boots_mod.generator, "ALTTPRPreset", lambda name: preset if name == "casualboots" else None)

    orch = BootsOrchestrator(
        BOOTS_DEFINITION, 1, presenter=AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=AsyncMock(),
    )
    result = await orch.roll()
    assert isinstance(result, SeedResult)
    assert result.seed is seed
    preset.generate.assert_awaited_once_with(allow_quickswap=True)


def test_boots_definition_matches_legacy_configuration():
    assert BOOTS_DEFINITION.event_slug == "boots"
    assert BOOTS_DEFINITION.racetime_category == "alttpr"
    assert BOOTS_DEFINITION.racetime_goal == "Beat the game - Tournament (Solo)"
    assert BOOTS_DEFINITION.guild_id == 973765801528139837
    assert BOOTS_DEFINITION.lang == "en"
    # legacy boots had no audit/commentary channels or helper roles
    assert BOOTS_DEFINITION.audit_channel_id is None
    assert BOOTS_DEFINITION.commentary_channel_id is None
    assert BOOTS_DEFINITION.helper_role_ids == []
