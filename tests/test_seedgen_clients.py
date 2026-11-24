"""Outbound clients that weren't covered elsewhere: SM DASH, VARIA (Choozo and
league playoffs), SM/SMZ3 multiworld, the alttpr.com daily, Sheets result
recording and the racetime.gg bot's start-up.

HTTP goes to the ``fake_http`` server; the pyz3r and gspread clients are mocks.
"""

import logging
from types import SimpleNamespace
from unittest import mock

import aiohttp
import gspread
import pytest

from alttprbot import models
from alttprbot.alttprgen import smvaria, smz3multi
from alttprbot.alttprgen.randomizer import smdash
from alttprbot.exceptions import InvalidInputError, SeedGenerationError
from alttprbot.services import daily, tournament_results

# ---------------------------------------------------------------------------
# SM DASH
# ---------------------------------------------------------------------------


@pytest.fixture
def dash(fake_http, monkeypatch):
    monkeypatch.setattr(smdash, "DASH_BASE", fake_http.url())
    return fake_http


async def test_create_smdash(dash):
    dash.add("GET", "/generate/classic_mm", body="https://dash.test/seed/abc", status=307, content_type="text/plain")
    assert await smdash.create_smdash(spoiler=True) == "https://dash.test/seed/abc"
    assert dash.requests[0].query == {"race": "1", "spoiler": "1"}


async def test_create_smdash_error(dash):
    dash.add("GET", "/generate/nope", body="Unknown mode", status=400, content_type="text/plain")
    with pytest.raises(SeedGenerationError, match="Could not generate smdash seed: Unknown mode"):
        await smdash.create_smdash(mode="nope")


async def test_smdash_presets_and_fallback(dash):
    dash.add("GET", "/api/presets", body='{"data": [{"tags": ["classic"]}, {"tags": ["sgl23", "x"]}]}')
    assert await smdash.get_smdash_presets() == ["classic", "sgl23"]

    dash.routes.clear()
    dash.add("GET", "/api/presets", body="<html>", content_type="text/html")
    assert "chozo_bozo" in await smdash.get_smdash_presets()


# ---------------------------------------------------------------------------
# VARIA
# ---------------------------------------------------------------------------


@pytest.fixture
def varia(monkeypatch):
    create = mock.AsyncMock(return_value=SimpleNamespace(guid="g", url="https://varia.test/seed"))
    monkeypatch.setattr(smvaria.SuperMetroidVaria, "create", create)
    return create


async def test_generate_preset(varia):
    await smvaria.generate_preset("default", "regular", race=True)
    varia.assert_awaited_once_with(skills_preset="regular", settings_preset="default", race=True)


async def test_generate_choozo_settings(varia):
    ctx = SimpleNamespace(send_message=mock.AsyncMock())

    seed = await smvaria.generate_choozo(ctx, True, "M/m", "VanillaArea", "VanillaBoss", "BasicDifficulty",
                                         "RandomEscape", "EarlyMorph", "VanillaStart")

    assert seed.url == "https://varia.test/seed"
    ctx.send_message.assert_awaited_once()
    kwargs = varia.await_args.kwargs
    assert (kwargs["settings_preset"], kwargs["skills_preset"], kwargs["race"], kwargs["raise_for_status"]) == (
        "Season_Races", "newbie", True, False)
    s = kwargs["settings_dict"]
    assert (s["majorsSplit"], s["areaRandomization"], s["areaLayout"]) == ("Major", "off", "off")
    assert (s["bossRandomization"], s["escapeRando"], s["maxDifficulty"], s["morphPlacement"]) == ("off", "on", "easy", "early")
    assert (s["startLocation"], s["startLocationMultiSelect"]) == ("Landing Site", ["Landing Site"])


async def test_generate_choozo_random_start_and_harder_skills(varia):
    ctx = SimpleNamespace(send_message=mock.AsyncMock())
    await smvaria.generate_choozo(ctx, False, "FullCountdown", "FullArea", "RandomBoss", "HardDifficulty",
                                  "VanillaEscape", "LateMorph", "DeepStart")
    kwargs = varia.await_args.kwargs
    s = kwargs["settings_dict"]
    assert kwargs["skills_preset"] == "Season_Races"
    assert (s["areaLayout"], s["bossRandomization"], s["escapeRando"], s["startLocation"]) == ("on", "on", "off", "random")
    assert s["startLocationMultiSelect"] == smvaria.CHOOZO_STARTS["DeepStart"]


async def test_generate_choozo_rejects_bad_choices_and_failed_seeds(monkeypatch):
    ctx = SimpleNamespace(send_message=mock.AsyncMock())
    with pytest.raises(ValueError, match="Invalid item split setting.  Must be "):
        await smvaria.generate_choozo(ctx, True, "Nope", "a", "b", "c", "d", "e", "f")

    monkeypatch.setattr(smvaria.SuperMetroidVaria, "create", mock.AsyncMock(return_value=SimpleNamespace(data="boom")))
    args = [next(iter(c)) for c in (smvaria.CHOOZO_SPLITS, smvaria.CHOOZO_AREAS, smvaria.CHOOZO_BOSSES,
                                    smvaria.CHOOZO_DIFFICULTIES, smvaria.CHOOZO_ESCAPES, smvaria.CHOOZO_MORPHS,
                                    smvaria.CHOOZO_STARTS)]
    with pytest.raises(SeedGenerationError, match="Error: boom"):
        await smvaria.generate_choozo(ctx, False, *args)


def test_require_choice_message():
    with pytest.raises(ValueError, match=r"^Invalid x setting\.  Must be a, b or c\.$"):
        smvaria._require_choice("z", {"a": 1, "b": 2, "c": 3}, "x")
    with pytest.raises(ValueError, match=r"^Invalid x setting\.  Must be a or b\.$"):
        smvaria._require_choice("z", ("a", "b"), "x")


@pytest.mark.parametrize(
    "majors, area, bosses, expected",
    [
        ("FullTraditional", "Off", "Off", {"majorsSplit": "Full", "areaRandomization": "off",
                                          "lightAreaRandomization": "off", "bossRandomization": "off"}),
        ("Major", "Light", "On", {"majorsSplit": "Major", "areaRandomization": "on", "lightAreaRandomization": "on",
                                  "bossRandomization": "on"}),
    ],
)
async def test_league_playoff_settings(varia, majors, area, bosses, expected):
    await smvaria.generate_league_playoff(majors, area, bosses)
    settings = varia.await_args.kwargs["settings_dict"]
    assert {k: settings[k] for k in expected} == expected
    assert "startLocation" not in settings


async def test_league_playoff_full_random_starts_anywhere(varia):
    await smvaria.generate_league_playoff("FullRandom", "Full", "On")
    settings = varia.await_args.kwargs["settings_dict"]
    assert settings["startLocation"] == "random" and len(settings["startLocationMultiSelect"]) == 8


@pytest.mark.parametrize("args, message", [(("x", "Off", "Off"), "Invalid major"), (("Major", "x", "Off"), "Invalid area"),
                                           (("Major", "Off", "x"), "Invalid bosses")])
async def test_league_playoff_validation(args, message):
    with pytest.raises(InvalidInputError, match=message):
        await smvaria.generate_league_playoff(*args)


# ---------------------------------------------------------------------------
# SM / SMZ3 multiworld
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("randomizer, client, preset", [("sm", "SMClient", "casual_full"), ("smz3", "SMZ3Client", "normal")])
async def test_generate_multiworld_settings(monkeypatch, randomizer, client, preset):
    create = mock.AsyncMock(return_value="SEED")
    monkeypatch.setattr(getattr(smz3multi, client), "create", create)

    seed = await smz3multi.generate_multiworld(preset, ["alice", "bob"], tournament=True, randomizer=randomizer,
                                               seed_number=42)

    assert seed == "SEED"
    settings = create.await_args.kwargs["settings"]
    assert (settings["race"], settings["gamemode"], settings["players"], settings["seed"]) == ("true", "multiworld", 2, "42")
    assert (settings["player-0"], settings["player-1"]) == ("alice", "bob")


# ---------------------------------------------------------------------------
# alttpr.com daily
# ---------------------------------------------------------------------------


async def test_check_for_new_daily_publishes_once(db, monkeypatch):
    published = []
    monkeypatch.setattr(daily.events, "publish", published.append)
    monkeypatch.setattr(daily, "find_daily_hash", mock.AsyncMock(return_value={"hash": "abc"}))

    await daily.check_for_new_daily()
    await daily.check_for_new_daily()

    assert [e.hash_id for e in published] == ["abc"]
    assert await models.Daily.filter(hash="abc").count() == 1


async def test_find_daily_hash_reads_alttpr(monkeypatch, fake_http):
    fake_http.add("GET", "/api/daily", body='{"hash": "xyz"}')
    real_request = aiohttp.request
    monkeypatch.setattr(daily.aiohttp, "request",
                        lambda method, url, **kw: real_request(method, url.replace("https://alttpr.com", fake_http.url()), **kw))
    await daily.find_daily_hash.cache.clear()
    assert await daily.find_daily_hash() == {"hash": "xyz"}
    await daily.find_daily_hash.cache.clear()


# ---------------------------------------------------------------------------
# Google Sheets result recording
# ---------------------------------------------------------------------------


class Workbook:
    def __init__(self, has_tab=True):
        self.has_tab = has_tab
        self.added = []
        self.wks = SimpleNamespace(append_row=mock.AsyncMock())

    async def worksheet(self, name):
        if not self.has_tab:
            raise gspread.exceptions.WorksheetNotFound(name)
        return self.wks

    async def add_worksheet(self, name, rows, cols):
        self.added.append((name, rows, cols))
        return self.wks


@pytest.fixture
def sheets(monkeypatch):
    books = {}
    agc = SimpleNamespace(open_by_key=mock.AsyncMock(side_effect=lambda key: books[key]))
    manager = SimpleNamespace(authorize=mock.AsyncMock(return_value=agc))
    monkeypatch.setattr(tournament_results.gspread_asyncio, "AsyncioGspreadClientManager", lambda creds: manager)
    return books


def event(gsheet_id):
    config = SimpleNamespace(data=SimpleNamespace(gsheet_id=gsheet_id, stream_delay=0))
    return SimpleNamespace(get_config=mock.AsyncMock(return_value=config))


async def test_record_results_writes_each_events_pending_races(db, monkeypatch, sheets, caplog):
    monkeypatch.setattr(tournament_results.tournaments, "TOURNAMENT_DATA", {
        "alttpr": event("sheet-a"), "nosheet": event(None), "quiet": event("sheet-q"),
    })
    sheets["sheet-a"] = book = Workbook(has_tab=False)
    sheets["sheet-q"] = Workbook()
    await models.TournamentResults.create(srl_id="alttpr/one", episode_id="1", event="alttpr")
    await models.TournamentResults.create(srl_id="alttpr/two", episode_id="2", event="alttpr")
    await models.TournamentResults.create(srl_id="alttpr/done", episode_id="3", event="alttpr", written_to_gsheet=1)

    recorded = []

    async def record(wks, race, settings):
        if race.srl_id == "alttpr/two":
            raise RuntimeError("racetime down")
        recorded.append(race.srl_id)

    monkeypatch.setattr(tournament_results, "_record_race", record)

    await tournament_results.record_results()

    assert recorded == ["alttpr/one"]
    assert book.added == [("alttpr", 50, 10)]
    book.wks.append_row.assert_awaited_once_with(values=tournament_results.SHEET_HEADER)
    assert "Encountered a problem when attempting to record a race." in caplog.text


# ---------------------------------------------------------------------------
# racetime.gg bot start-up
# ---------------------------------------------------------------------------


@pytest.fixture
def rt_bot(monkeypatch):
    from alttprbot_racetime import core

    bot = core.SahasrahBotRaceTimeBot(handler_class="H", category_slug="alttpr", client_id="id",
                                      client_secret="secret", logger=logging.getLogger("rt-test"))
    return bot


def test_racetime_bot_handler_kwargs(rt_bot):
    assert rt_bot.get_handler_class() == "H"
    kwargs = rt_bot.get_handler_kwargs("ws", {"s": 1})
    assert (kwargs["conn"], kwargs["state"], kwargs["command_prefix"]) == ("ws", {"s": 1}, "!")


@pytest.mark.parametrize(
    "authorize, ok, message",
    [
        (mock.AsyncMock(return_value=("tok", 3600)), True, None),
        (mock.AsyncMock(return_value=None), False, "authorize() returned None"),
        (mock.AsyncMock(side_effect=aiohttp.ClientResponseError(mock.Mock(real_url="x"), (), status=401)), False,
         "401 Unauthorized"),
    ],
)
async def test_racetime_bot_authorize(rt_bot, caplog, authorize, ok, message):
    rt_bot.authorize = authorize
    assert await rt_bot._authorize() is ok
    if ok:
        assert (rt_bot.access_token, rt_bot.reauthorize_every) == ("tok", 3600)
    else:
        assert message in caplog.text


async def test_racetime_bot_authorize_other_http_errors_raise(rt_bot):
    rt_bot.authorize = mock.AsyncMock(side_effect=aiohttp.ClientResponseError(mock.Mock(real_url="x"), (), status=500))
    with pytest.raises(aiohttp.ClientResponseError):
        await rt_bot._authorize()


@pytest.mark.parametrize(
    "data, rejoined, forgotten",
    [
        ({"status": {"value": "open"}, "unlisted": True}, True, False),
        ({"status": {"value": "finished"}, "unlisted": True}, False, True),
        ({"status": {"value": "open"}, "unlisted": False}, False, True),
    ],
)
async def test_resume_unlisted_room(db, rt_bot, fake_http, monkeypatch, data, rejoined, forgotten):
    import json

    from alttprbot.services import racetime_rooms

    fake_http.add("GET", "/alttpr/room-1/data", body=json.dumps(data))
    monkeypatch.setattr(rt_bot, "http_uri", lambda path: fake_http.url(path))
    rt_bot.http = aiohttp.ClientSession()
    rt_bot.join_race_room = mock.AsyncMock()
    await models.RTGGUnlistedRooms.create(room_name="alttpr/room-1", category="alttpr")
    try:
        await rt_bot._resume_unlisted_room("alttpr/room-1")
    finally:
        await rt_bot.http.close()

    assert rt_bot.join_race_room.await_count == int(rejoined)
    assert (await racetime_rooms.unlisted_rooms("alttpr") == []) is forgotten


async def test_racetime_bot_start_resumes_unlisted_rooms(db, rt_bot, monkeypatch):
    rt_bot._authorize = mock.AsyncMock(return_value=True)
    rt_bot.reauthorize = mock.Mock(return_value="reauth")
    rt_bot.refresh_races = mock.Mock(return_value="refresh")
    rt_bot.loop = mock.Mock()
    rt_bot._resume_unlisted_room = mock.AsyncMock()
    await models.RTGGUnlistedRooms.create(room_name="alttpr/a", category="alttpr")
    await models.RTGGUnlistedRooms.create(room_name="smz3/b", category="smz3")

    await rt_bot.start()
    await rt_bot.http.close()

    rt_bot._resume_unlisted_room.assert_awaited_once_with("alttpr/a")
    assert [c.args[0] for c in rt_bot.loop.create_task.call_args_list] == ["reauth", "refresh"]


async def test_racetime_bot_start_stops_when_unauthorized(rt_bot):
    rt_bot._authorize = mock.AsyncMock(return_value=False)
    rt_bot.loop = mock.Mock()
    await rt_bot.start()
    await rt_bot.http.close()
    rt_bot.loop.create_task.assert_not_called()
