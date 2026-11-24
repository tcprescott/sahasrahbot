"""The concrete tournament classes: the generic ALTTPR tournament race
(alttprbot/tournament/alttpr.py), the ALTTPR leagues (alttprleague.py) and the
SpeedGaming dailies (dailies/).

Built with ``make_race`` from ``tests/test_tournament.py``; seed embeds, the bots
and the league API are fakes.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import models
from alttprbot.exceptions import SahasrahBotException
from alttprbot.services import bots
from alttprbot.tournament import alttpr, alttprleague, dailies
from alttprbot.tournament.dailies import core as daily_core
from tests.test_tournament import episode, make_race


@pytest.fixture
def discord_bot(monkeypatch):
    monkeypatch.setattr(bots, "_discord_client", SimpleNamespace(emojis=["E"]))


@pytest.fixture
def embeds(monkeypatch):
    async def public(seed, **kwargs):
        return discord.Embed(title=kwargs["name"], description=kwargs["notes"])

    async def tournament(seed, **kwargs):
        return discord.Embed(title=f"T {kwargs['name']}")

    monkeypatch.setattr(alttpr, "seed_embed", public)
    monkeypatch.setattr(alttpr, "seed_tournament_embed", tournament)


def alttpr_race(cls=alttpr.ALTTPRTournamentRace, **config):
    race = make_race(cls=cls, **config)
    race.rtgg_handler.bot = mock.Mock(http_uri=lambda path: f"https://racetime.test{path}")
    race.rtgg_handler.data = {"url": "/alttpr/room-1", "name": "alttpr/room-1",
                              "entrants": [{"user": {"id": "rt-a"}}, {"user": {"id": "rt-b"}}]}
    race.seed = SimpleNamespace(url="https://alttpr.test/h/abc", code=["Bow", "Bombs", "Hookshot", "Lamp", "Map"])
    return race


def names(embed):
    return [f.name for f in embed.fields]


async def test_create_embeds(discord_bot, embeds):
    race = alttpr_race()
    await race.create_embeds()
    assert race.embed.title == race.race_info and race.embed.description == "Alice vs. Bob"
    assert names(race.embed) == ["Broadcast Channels", "RaceTime.gg"]
    assert race.embed.fields[0].value == "[ALTTPRandomizer](https://twitch.tv/ALTTPRandomizer)"
    assert race.tournament_embed.fields[1].value == "https://racetime.test/alttpr/room-1"

    race.episode["channels"] = []
    await race.create_embeds()
    assert names(race.embed) == ["RaceTime.gg"]

    race.rtgg_handler = None
    with pytest.raises(SahasrahBotException, match="No RaceTime.gg handler"):
        await race.create_embeds()


async def test_seed_code_and_bracket_settings():
    race = alttpr_race()
    assert race.seed_code == "(Bow/Bombs/Hookshot/Lamp/Map)"
    assert race.bracket_settings is None
    await race.roll()  # the base class rolls nothing


async def test_process_tournament_race(db, discord_bot, embeds, monkeypatch):
    race = alttpr_race()
    race.update_data = mock.AsyncMock()
    race.send_audit_message = mock.AsyncMock()
    race.send_commentary_message = mock.AsyncMock()
    race.send_player_message = mock.AsyncMock()

    await race.process_tournament_race([], {})

    race.update_data.assert_awaited_once()
    race.rtgg_handler.set_bot_raceinfo.assert_awaited_once_with("(Bow/Bombs/Hookshot/Lamp/Map)")
    race.send_audit_message.assert_awaited_once_with(embed=race.embed)
    race.send_commentary_message.assert_awaited_once_with(race.tournament_embed)
    assert [c.args[0] for c in race.send_player_message.await_args_list] == ["Alice", "Bob"]
    dms = [c for c in race.rtgg_handler.send_message.await_args_list if "direct_to" in c.kwargs]
    assert [(c.args[0], c.kwargs["direct_to"]) for c in dms] == [("https://alttpr.test/h/abc", "rt-a"),
                                                                 ("https://alttpr.test/h/abc", "rt-b")]
    result = await models.TournamentResults.get(srl_id="alttpr/room-1")
    assert (result.episode_id, result.event, result.permalink) == ("12345", "alttpr", "https://alttpr.test/h/abc")
    assert race.rtgg_handler.seed_rolled is True


async def test_send_room_welcome_pins_roll_button():
    race = alttpr_race()
    await race.send_room_welcome()
    pinned = race.rtgg_handler.send_message.await_args_list[1]
    assert pinned.args == ("Tournament Controls:",) and pinned.kwargs["pinned"] is True
    assert pinned.kwargs["actions"][0].data["message"] == "!tournamentrace"


async def test_alttpr_send_race_submission_form(db):
    race = alttpr_race()

    await race.send_race_submission_form()
    msg = race.players[0].discord_user.send.await_args.args[0]
    assert msg.startswith("Greetings!  Do not forget to submit settings")
    game = await models.TournamentGames.get(episode_id=12345)
    assert game.submitted == 1

    race.tournament_game = game
    race.players[0].discord_user.send.reset_mock()
    await race.send_race_submission_form()  # already submitted: no reminder
    race.players[0].discord_user.send.assert_not_awaited()

    await race.send_race_submission_form(warning=True)
    assert "cannot be created because settings have not submitted" in race.players[0].discord_user.send.await_args.args[0]


async def test_alttpr_submission_form_skipped_with_bracket_settings(db, monkeypatch):
    monkeypatch.setattr(alttpr.ALTTPRTournamentRace, "bracket_settings", property(lambda self: {"x": 1}))
    race = alttpr_race()
    await race.send_race_submission_form()
    race.players[0].discord_user.send.assert_not_awaited()


async def test_alttpr2024_configuration(monkeypatch):
    config = object()
    monkeypatch.setattr(alttpr.event_settings, "tournament_config", lambda slug: (slug, config))
    assert await alttpr.ALTTPR2024Race().configuration() == ("alttpr", config)


# ---------------------------------------------------------------------------
# Leagues
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls, slug", [(alttprleague.ALTTPRLeague, "invleague"),
                                       (alttprleague.ALTTPROpenLeague, "alttprleague")])
async def test_league_configuration(monkeypatch, cls, slug):
    monkeypatch.setattr(alttprleague.event_settings, "tournament_config", lambda s: s)
    assert await cls().configuration() == slug


async def test_league_roll_preset_and_spoiler(monkeypatch, discord_bot, embeds):
    race = alttpr_race(cls=alttprleague.ALTTPRLeague)
    generate = mock.AsyncMock(return_value=race.seed)
    monkeypatch.setattr(alttprleague.generator.ALTTPRPreset, "generate", generate)
    race.league_data = {"preset": "open", "spoiler": False}

    await race.roll()
    generate.assert_awaited_once_with(allow_quickswap=True, tournament=True, hints=False, spoilers="off")

    spoiler = SimpleNamespace(seed=race.seed, spoiler_log_url="https://spoilers.test/x")
    make_spoiler = mock.AsyncMock(return_value=spoiler)
    monkeypatch.setattr(alttprleague.spoilers, "generate_spoiler_game", make_spoiler)
    race.league_data = {"preset": "open", "spoiler": True}
    await race.roll()
    make_spoiler.assert_awaited_once_with("open")
    race.rtgg_handler.schedule_spoiler_race.assert_awaited_once_with("https://spoilers.test/x", 0)


class LeagueAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, method, url, params):
        self.calls.append((method, url, params))
        api = self

        class Response:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def json(self):
                return api.payload

        return Response()


async def test_league_data_from_api(monkeypatch):
    api = LeagueAPI({"mode": {"preset": "open", "coop": False, "spoiler": False}})
    monkeypatch.setattr(alttprleague.aiohttp, "request", api)
    race = alttpr_race(cls=alttprleague.ALTTPRLeague)

    await race.get_league_data()

    assert api.calls == [("get", "https://alttprleague.com/api/episode", {"id": 12345})]
    assert race.league_data["preset"] == "open"


async def test_league_without_mode_tells_the_room(monkeypatch):
    monkeypatch.setattr(alttprleague.aiohttp, "request", LeagueAPI({}))
    race = alttpr_race(cls=alttprleague.ALTTPRLeague)
    await race.get_league_data()
    assert "No active League mode!" in race.rtgg_handler.send_message.await_args.args[0]


async def test_league_update_data_also_fetches_league(monkeypatch):
    base = mock.AsyncMock()
    monkeypatch.setattr(alttprleague.ALTTPRTournamentRace, "update_data", base)
    race = alttpr_race(cls=alttprleague.ALTTPRLeague)
    race.get_league_data = mock.AsyncMock()
    await race.update_data(update_episode=False)
    base.assert_awaited_once_with(update_episode=False)
    race.get_league_data.assert_awaited_once()


@pytest.mark.parametrize("mode, goal, team_race", [
    ({"coop": False, "spoiler": False}, "Beat the game - Tournament (Solo)", False),
    ({"coop": True, "spoiler": False}, "Beat the game - Tournament (Co-op)", True),
    ({"coop": False, "spoiler": True}, "Beat the game - Tournament (Co-op)", False),
])
async def test_league_race_room_options(mode, goal, team_race):
    race = alttpr_race(cls=alttprleague.ALTTPRLeague)
    race.league_data = mode
    race.rtgg_bot = mock.Mock(startrace=mock.AsyncMock(return_value="handler"))

    assert await race.create_race_room() == "handler"

    kwargs = race.rtgg_bot.startrace.await_args.kwargs
    assert (kwargs["goal"], kwargs["team_race"], kwargs["invitational"]) == (goal, team_race, True)


# ---------------------------------------------------------------------------
# SpeedGaming dailies
# ---------------------------------------------------------------------------


def daily(cls, title="Daily Race", channels=("ALTTPRandomizer",)):
    race = make_race(cls=cls)
    race.episode = episode(channels=channels)
    race.episode["match1"]["title"] = title
    race.episode["id"] = 777
    race.episodeid = 777
    return race


def test_alttpr_daily_race_info():
    race = daily(dailies.AlttprSGDailyRace)
    # the race "starts" at SpeedGaming's countdown time (19:50 Eastern), seed ten minutes earlier
    assert race.race_info == ("SpeedGaming Daily Race Series - Daily Race at 7:50 PM Eastern on ALTTPRandomizer"
                              " - Seed Distributed at 7:40 PM Eastern - 777")
    assert race.seed_time == datetime(2024, 6, 1, 23, 40, tzinfo=timezone.utc)
    assert race.player_racetime_ids == []


def test_core_daily_race_info_and_seed_time():
    race = daily(daily_core.SGDailyRaceCore, channels=())
    assert race.race_info == ("SpeedGaming Daily Race Series - Daily Race at 7:50 PM Eastern"
                              " - Seed Distributed at 7:40 PM Eastern - 777")
    assert (race.race_start_time - race.seed_time).total_seconds() == 600


def test_smz3_weekly_race_info():
    race = daily(dailies.SMZ3DailyRace)
    assert race.race_info == "SMZ3 Weekly Race - Daily Race at 7:50 PM Eastern on ALTTPRandomizer - 777"


@pytest.mark.parametrize("cls", [daily_core.SGDailyRaceCore, dailies.SMZ3DailyRace])
@pytest.mark.parametrize("title, team_race", [("Co-op Race", True), ("Open", False)])
async def test_daily_race_rooms_are_open_and_coop_by_title(cls, title, team_race):
    race = daily(cls, title=title)
    race.rtgg_bot = mock.Mock(startrace=mock.AsyncMock(return_value="handler"))

    assert await race.create_race_room() == "handler"

    kwargs = race.rtgg_bot.startrace.await_args.kwargs
    assert (kwargs["goal"], kwargs["invitational"], kwargs["team_race"]) == ("Beat the game", False, team_race)


@pytest.mark.parametrize("cls, slug", [(dailies.AlttprSGDailyRace, "alttprdaily"), (dailies.SMZ3DailyRace, "smz3")])
async def test_daily_configuration(monkeypatch, cls, slug):
    monkeypatch.setattr(dailies.alttprdaily.event_settings, "tournament_config", lambda s: s)
    assert await cls().configuration() == slug


async def test_daily_room_opened_event_carries_seed_time():
    race = daily(dailies.AlttprSGDailyRace)
    race.rtgg_bot = mock.Mock(http_uri=lambda path: f"https://racetime.test{path}")
    race.rtgg_handler.data = {"url": "/alttpr/room", "name": "alttpr/room"}
    event = race.room_opened_event()
    assert event.seed_time == race.seed_time


async def test_daily_update_data(db, monkeypatch):
    monkeypatch.setattr(daily_core.speedgaming, "get_episode", mock.AsyncMock(return_value={"id": 777}))
    rtgg_bot = mock.Mock(get_team=mock.AsyncMock(return_value={"members": []}))
    monkeypatch.setattr(bots, "_racetime_bots", {"alttpr": rtgg_bot})
    await models.TournamentGames.create(episode_id=777, event="alttprdaily")
    race = daily(dailies.AlttprSGDailyRace)

    await race.update_data()

    assert race.episode == {"id": 777}
    assert race.tournament_game.event == "alttprdaily"
    assert race.rtgg_bot is rtgg_bot
    rtgg_bot.get_team.assert_awaited_once_with("sg-volunteers")
