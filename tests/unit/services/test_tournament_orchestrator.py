"""Unit tests for the TournamentOrchestrator (mocked presenter/gateway/resolvers/repos)."""

from unittest.mock import AsyncMock

import pytest

from alttprbot.services.tournament import TournamentDefinition
from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.types import RaceRoom, TournamentPlayer

EPISODE = {
    "id": 100,
    "event": {"shortName": "TestEvent", "slug": "test"},
    "match1": {
        "title": "Round 1",
        "players": [
            {"discordId": "1", "discordTag": "a", "displayName": "A", "publicStream": "yes", "streamingFrom": "twitchA"},
            {"discordId": "2", "discordTag": "b", "displayName": "B", "publicStream": "yes", "streamingFrom": "twitchB"},
            {"discordId": "9", "discordTag": "ignore", "displayName": "I", "publicStream": "ignore", "streamingFrom": ""},
        ],
    },
    "channels": [{"name": "restreamA"}, {"name": "has space"}],
    "whenCountdown": "2026-06-26T18:00:00-04:00",
    "when": "2026-06-26T18:30:00-04:00",
}


def _definition(**kw):
    base = dict(event_slug="test", racetime_category="test", racetime_goal="Beat the game")
    base.update(kw)
    return TournamentDefinition(**base)


def _orchestrator(definition=None, *, player_resolver=None, gatekeep_checker=None, racetime=None, presenter=None):
    return TournamentOrchestrator(
        definition or _definition(),
        100,
        presenter=presenter or AsyncMock(),
        player_resolver=player_resolver or AsyncMock(),
        gatekeep_checker=gatekeep_checker or AsyncMock(return_value=False),
        racetime=racetime or AsyncMock(),
    )


async def _player_resolver(player):
    return TournamentPlayer(rtgg_id=f"rt{player['discordId']}", name=player["displayName"], discord_user_id=int(player["discordId"]))


async def test_update_data_resolves_players_skipping_ignored(monkeypatch):
    racetime = AsyncMock()
    racetime.get_team = AsyncMock(return_value={"members": []})
    orch = _orchestrator(player_resolver=_player_resolver, racetime=racetime)
    orch.episode = EPISODE
    # avoid hitting speedgaming / repos
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=None))

    await orch.update_data(update_episode=False)

    assert orch.player_names == ["A", "B"]  # "ignore" player skipped
    assert orch.player_racetime_ids == ["rt1", "rt2"]
    assert orch.player_discord_ids == [1, 2]
    racetime.get_team.assert_awaited_once_with("test", "sg-volunteers")


def test_pure_properties_match_legacy_formatting():
    orch = _orchestrator()
    orch.episode = EPISODE
    orch.players = [
        TournamentPlayer("rt1", "A", 1),
        TournamentPlayer("rt2", "B", 2),
    ]
    assert orch.event_name == "TestEvent"
    assert orch.event_slug == "test"
    assert orch.versus == "A vs. B"
    assert orch.broadcast_channels == ["restreamA"]  # "has space" excluded
    assert "TestEvent - A vs. B - Round 1" in orch.race_info
    assert orch.race_info.endswith(" - 100")


def test_versus_uses_comma_for_more_than_two():
    orch = _orchestrator()
    orch.players = [TournamentPlayer(None, n, None) for n in ("A", "B", "C")]
    assert orch.versus == "A, B, C"


async def test_on_room_created_persists_invites_and_sends(monkeypatch):
    racetime = AsyncMock()
    presenter = AsyncMock()
    orch = _orchestrator(racetime=racetime, presenter=presenter)
    orch.episode = EPISODE
    orch.players = [TournamentPlayer("rt1", "A", 1), TournamentPlayer("rt2", "B", 2)]

    import alttprbot.services.tournament.core as core_mod
    upsert = AsyncMock()
    monkeypatch.setattr(core_mod.TournamentResultsRepository, "upsert_by_srl_id", upsert)

    room = RaceRoom(name="test/clever-cat", url="http://rt/test/clever-cat")
    await orch.on_room_created(room)

    upsert.assert_awaited_once()
    assert upsert.call_args.kwargs["srl_id"] == "test/clever-cat"
    assert upsert.call_args.kwargs["defaults"]["event"] == "test"
    assert [c.args for c in racetime.invite_user.await_args_list] == [("test/clever-cat", "rt1"), ("test/clever-cat", "rt2")]
    presenter.send_player_room_info.assert_awaited_once()


async def test_can_gatekeep_team_member_short_circuits():
    racetime = AsyncMock()
    orch = _orchestrator(racetime=racetime)
    orch.restream_team = {"members": [{"id": "rtX"}]}
    assert await orch.can_gatekeep("rtX") is True  # on the restream team


async def test_can_gatekeep_delegates_role_check(monkeypatch):
    checker = AsyncMock(return_value=True)
    orch = _orchestrator(definition=_definition(helper_role_ids=[55]), gatekeep_checker=checker)
    orch.restream_team = {"members": []}

    import alttprbot.services.tournament.core as core_mod
    user = type("U", (), {"discord_user_id": 777})()
    monkeypatch.setattr(core_mod.UserRepository, "get_by_rtgg_id", AsyncMock(return_value=user))

    assert await orch.can_gatekeep("rtY") is True
    checker.assert_awaited_once_with(777, [55])


async def test_can_gatekeep_false_when_user_unknown(monkeypatch):
    orch = _orchestrator()
    orch.restream_team = {"members": []}
    import alttprbot.services.tournament.core as core_mod
    monkeypatch.setattr(core_mod.UserRepository, "get_by_rtgg_id", AsyncMock(return_value=None))
    assert await orch.can_gatekeep("nobody") is False
