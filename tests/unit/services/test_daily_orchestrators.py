"""Unit tests for the SG daily/weekly orchestrators (PR7).

Covers the open-race specifics: non-invitational room kwargs (+ co-op team detection), the
custom race-info, the no-player-resolution update_data, and the channel/webhook announcement
(in place of player room-info DMs).
"""

from unittest.mock import AsyncMock

from alttprbot.services.tournament.core import TournamentOrchestrator
from alttprbot.services.tournament.dailies import (
    ALTTPR_DAILY_DEFINITION,
    SMZ3_DAILY_DEFINITION,
    AlttprSGDailyOrchestrator,
    SGDailyOrchestrator,
    SMZ3DailyOrchestrator,
)
from alttprbot.services.tournament.types import RaceRoom


def _episode(title="Daily Race"):
    return {
        "id": 100,
        "event": {"shortName": "Daily", "slug": "alttprdaily"},
        "match1": {"title": title, "players": [{"discordId": "1", "discordTag": "a", "displayName": "A", "publicStream": "yes", "streamingFrom": "t"}]},
        "channels": [{"name": "restreamA"}],
        "whenCountdown": "2026-06-26T18:00:00-04:00",
        "when": "2026-06-26T18:30:00-04:00",
    }


def _orch(cls, definition, *, presenter=None, racetime=None, title="Daily Race"):
    orch = cls(
        definition, 100,
        presenter=presenter or AsyncMock(), player_resolver=AsyncMock(),
        gatekeep_checker=AsyncMock(), racetime=racetime or AsyncMock(),
    )
    orch.episode = _episode(title)
    orch.room = RaceRoom(name="alttpr/daily", url="http://rt/daily", entrant_ids=[])
    return orch


def test_dailies_extend_base_orchestrator():
    assert issubclass(SGDailyOrchestrator, TournamentOrchestrator)
    assert issubclass(AlttprSGDailyOrchestrator, SGDailyOrchestrator)
    assert issubclass(SMZ3DailyOrchestrator, SGDailyOrchestrator)


def test_room_kwargs_not_invitational_and_solo():
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION, title="Daily Race")
    kw = orch.room_creation_kwargs
    assert kw["invitational"] is False
    assert kw["team_race"] is False
    # base kwargs preserved
    assert kw["unlisted"] is False and kw["auto_start"] is True


def test_room_kwargs_coop_title_enables_team_race():
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION, title="ALTTPR Co-op Daily")
    assert orch.room_creation_kwargs["team_race"] is True


def test_alttpr_daily_race_info_includes_seed_line():
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION, title="Daily 1")
    info = orch.race_info
    assert info.startswith("SpeedGaming Daily Race Series - Daily 1 at ")
    assert "Eastern" in info
    assert "Seed Distributed at " in info
    assert " on restreamA" in info
    assert info.endswith(" - 100")


def test_smz3_race_info_has_no_seed_line():
    orch = _orch(SMZ3DailyOrchestrator, SMZ3_DAILY_DEFINITION, title="Weekly 1")
    info = orch.race_info
    assert info.startswith("SMZ3 Weekly Race - Weekly 1 at ")
    assert "Seed Distributed" not in info
    assert info.endswith(" - 100")


def test_seed_time_is_ten_minutes_before_start():
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION)
    assert (orch.race_start_time - orch.seed_time).total_seconds() == 600


async def test_update_data_resolves_no_players(monkeypatch):
    racetime = AsyncMock()
    racetime.get_team = AsyncMock(return_value={"members": []})
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION, racetime=racetime)

    import alttprbot.services.tournament.dailies as dailies_mod
    monkeypatch.setattr(dailies_mod.speedgaming, "get_episode", AsyncMock(return_value=_episode()))
    monkeypatch.setattr(dailies_mod.TournamentGamesRepository, "get_by_episode_id", AsyncMock(return_value=None))

    await orch.update_data()

    assert orch.players == []  # open race: episode players are NOT resolved/invited
    assert orch.player_racetime_ids == []
    racetime.get_team.assert_awaited_once_with("alttpr", "sg-volunteers")


async def test_alttpr_daily_announcement_passes_seed_and_webhook():
    presenter = AsyncMock()
    orch = _orch(AlttprSGDailyOrchestrator, ALTTPR_DAILY_DEFINITION, presenter=presenter, title="Daily 1")
    await orch.send_player_room_info()

    call = presenter.send_race_announcement.await_args
    assert call.args[0] == ALTTPR_DAILY_DEFINITION.announce_channel_id
    kw = call.kwargs
    assert kw["series"] == "SpeedGaming Daily Race Series"
    assert kw["prefix"] == ""
    assert kw["seed_time"] is not None  # alttprdaily includes the seed-distribution time
    assert kw["webhook_url"] == AlttprSGDailyOrchestrator.webhook_url
    assert kw["webhook_role_mention"] == "<@&399038388964950016>"
    assert kw["room_url"] == "http://rt/daily"
    assert kw["title"] == "Daily 1"


async def test_smz3_announcement_has_prefix_no_seed_no_webhook():
    presenter = AsyncMock()
    orch = _orch(SMZ3DailyOrchestrator, SMZ3_DAILY_DEFINITION, presenter=presenter, title="Weekly 1")
    await orch.send_player_room_info()

    call = presenter.send_race_announcement.await_args
    assert call.args[0] == SMZ3_DAILY_DEFINITION.announce_channel_id
    kw = call.kwargs
    assert kw["series"] == "SMZ3 Weekly Race"
    assert kw["prefix"] == "<@&449260882501959700> "
    assert kw["seed_time"] is None  # smz3 announcement omits the seed-distribution time
    assert kw["webhook_url"] is None  # no webhook for smz3


def test_daily_definitions():
    assert ALTTPR_DAILY_DEFINITION.event_slug == "alttprdaily"
    assert ALTTPR_DAILY_DEFINITION.racetime_category == "alttpr"
    assert ALTTPR_DAILY_DEFINITION.racetime_goal == "Beat the game - Casual"
    assert ALTTPR_DAILY_DEFINITION.guild_id == 307860211333595146
    assert ALTTPR_DAILY_DEFINITION.announce_channel_id == 307861467838021633
    assert ALTTPR_DAILY_DEFINITION.room_open_time == 60

    assert SMZ3_DAILY_DEFINITION.event_slug == "smz3"
    assert SMZ3_DAILY_DEFINITION.racetime_category == "smz3"
    assert SMZ3_DAILY_DEFINITION.racetime_goal == "Beat the games"
    assert SMZ3_DAILY_DEFINITION.guild_id == 445948207638511616
    assert SMZ3_DAILY_DEFINITION.announce_channel_id == 451977523123978260
    assert SMZ3_DAILY_DEFINITION.room_open_time == 60
