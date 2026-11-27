"""Tests for the HTTP clients in alttprbot/integrations/ and the services built on
them: racer verification (alttprbot/services/racer_verification.py), tournament
result recording (alttprbot/services/tournament_results.py) and opening a
tournament room (alttprbot/services/tournament_jobs.py).

HTTP goes to a local fake server (the ``fake_http`` fixture).
"""
import datetime
import json
from types import SimpleNamespace
from unittest import mock

import pytest

import config
from alttprbot import models, tournaments
from alttprbot.integrations import alttprladder, holyimage, racetime
from alttprbot.services import bots, tournament_jobs, tournament_results
from alttprbot.services import racer_verification as verification


@pytest.fixture
def racetime_site(fake_http, monkeypatch):
    monkeypatch.setattr(config, "RACETIME_URL", fake_http.url())
    return fake_http


# ---------------------------------------------------------------------------
# racetime.gg
# ---------------------------------------------------------------------------


async def test_get_race_and_user_default_to_racetime_url(racetime_site):
    racetime_site.add("GET", "/alttpr/room/data", body=json.dumps({"name": "alttpr/room"}))
    racetime_site.add("GET", "/user/abc/data", body=json.dumps({"full_name": "Abc#1"}))
    assert await racetime.get_race("alttpr/room") == {"name": "alttpr/room"}
    assert await racetime.get_user("abc") == {"full_name": "Abc#1"}


async def test_get_user_uses_given_base_url(fake_http):
    fake_http.add("GET", "/user/abc/data", body=json.dumps({"url": "/user/abc"}), content_type="text/plain")
    # parsed from the raw body, whatever the Content-Type
    assert await racetime.get_user("abc", base_url=fake_http.url()) == {"url": "/user/abc"}


async def test_get_race_raises_on_http_error(racetime_site):
    import aiohttp

    racetime_site.add("GET", "/alttpr/gone/data", status=404)
    with pytest.raises(aiohttp.ClientResponseError):
        await racetime.get_race("alttpr/gone")


async def test_get_user_races_page_returns_none_for_html(racetime_site):
    racetime_site.add("GET", "/user/abc/races/data", body="<html></html>", content_type="text/html")
    assert await racetime.get_user_races_page("abc", 1) is None
    assert racetime_site.requests[0].query == {"page": "1"}


@pytest.mark.parametrize(
    "race_data",
    [{"url": "/r", "recorded": True, "recordable": True}, {"url": "/r", "recorded": False, "recordable": False}, {"url": "/r"}],
)
async def test_record_race_skips_recorded_or_unrecordable(racetime_site, race_data):
    await racetime.record_race(race_data)
    assert racetime_site.requests == []


async def test_record_race_posts_with_csrf_token(racetime_site):
    racetime_site.add("GET", "/alttpr/room", body='<form><input name="csrfmiddlewaretoken" value="tok"></form>', content_type="text/html")
    racetime_site.add("POST", "/alttpr/room/monitor/record")
    await racetime.record_race({"url": "/alttpr/room", "recorded": False, "recordable": True})
    assert [(r.method, r.path) for r in racetime_site.requests] == [("GET", "/alttpr/room"), ("POST", "/alttpr/room/monitor/record")]
    assert racetime_site.requests[1].body == "csrfmiddlewaretoken=tok"


async def test_record_race_without_token_page_raises(racetime_site):
    racetime_site.add("GET", "/alttpr/room", status=403)
    with pytest.raises(Exception, match="Unable to acquire CSRF token"):
        await racetime.record_race({"url": "/alttpr/room", "recorded": False, "recordable": True})


async def test_record_race_failed_post_is_only_logged(racetime_site):
    racetime_site.add("GET", "/alttpr/room", body='<input name="csrfmiddlewaretoken" value="tok">', content_type="text/html")
    racetime_site.add("POST", "/alttpr/room/monitor/record", status=500)
    await racetime.record_race({"url": "/alttpr/room", "recorded": False, "recordable": True})


# ---------------------------------------------------------------------------
# ALTTPR Ladder
# ---------------------------------------------------------------------------


@pytest.fixture
def ladder_site(fake_http, monkeypatch):
    monkeypatch.setattr(alttprladder, "LADDER_API", fake_http.url("/api"))
    monkeypatch.setattr(alttprladder, "ARCHIVE_API", fake_http.url("/archive"))
    return fake_http


async def test_ladder_racer_guid_and_history(ladder_site):
    ladder_site.add("GET", "/api/GetActiveRacers", body=json.dumps([
        {"DiscordName": "someone", "RacerGUID": "g1"}, {"DiscordName": "runner", "RacerGUID": "g2"},
    ]))
    ladder_site.add("GET", "/api/GetRacerHistory", body=json.dumps([{"Results": []}]))
    assert await alttprladder.get_racer_guid("runner") == "g2"
    assert await alttprladder.get_racer_guid("nobody") is None
    assert await alttprladder.get_racer_history("g2") == [{"Results": []}]
    assert ladder_site.requests[-1].query == {"RacerGUID": "g2", "flag_id": "0"}


async def test_ladder_archive_count_formats_dates(ladder_site):
    ladder_site.add("GET", "/archive/GetRacerRaceHistory", body=json.dumps({"TotalCount": 7}))
    count = await alttprladder.get_archive_race_count(
        123, start=datetime.datetime(2025, 1, 2), end=datetime.datetime(2026, 3, 4))
    assert count == 7
    assert ladder_site.requests[0].query == {"discordid": "123", "startdt": "01022025", "enddt": "03042026"}


# ---------------------------------------------------------------------------
# Holy images
# ---------------------------------------------------------------------------


async def test_holy_images_index(fake_http, monkeypatch):
    monkeypatch.setattr(holyimage, "INDEX_URL", fake_http.url("/holyimages.json"))
    fake_http.add("GET", "/holyimages.json", body=json.dumps({"z3r": [{"slug": "bow", "idx": 1}]}), content_type="text/plain")
    assert await holyimage.get_holy_images() == {"z3r": [{"slug": "bow", "idx": 1}]}


# ---------------------------------------------------------------------------
# Racer verification service
# ---------------------------------------------------------------------------


def _race(slug, status="finished", days_ago=1):
    opened = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return {"category": {"slug": slug}, "status": {"value": status}, "opened_at": opened.isoformat()}


async def test_racetime_count_filters_and_pages(monkeypatch):
    pages = {
        1: {"num_pages": 2, "races": [_race("alttpr"), _race("smz3"), _race("alttpr", status="cancelled"), _race("alttpr", days_ago=400)]},
        2: {"num_pages": 2, "races": [_race("alttpr")]},
        3: {"num_pages": 2, "races": []},
    }
    get_page = mock.AsyncMock(side_effect=lambda rid, page: pages[page])
    monkeypatch.setattr(racetime, "get_user_races_page", get_page)

    assert await verification.get_racetime_count("abc", ["alttpr"], days=365, max_count=10) == 2
    assert [c.args for c in get_page.call_args_list] == [("abc", 1), ("abc", 2), ("abc", 3)]

    get_page.reset_mock()
    assert await verification.get_racetime_count("abc", ["alttpr"], max_count=1) == 1  # stops once max_count is reached
    assert get_page.call_count == 1

    assert await verification.get_racetime_count("abc", None) == 0


async def test_racetime_count_stops_on_non_json(monkeypatch):
    monkeypatch.setattr(racetime, "get_user_races_page", mock.AsyncMock(return_value=None))
    assert await verification.get_racetime_count("abc", ["alttpr"], max_count=5) == 0


async def test_ladder_count_counts_recent_results(monkeypatch):
    recent = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
    old = (datetime.datetime.now() - datetime.timedelta(days=500)).isoformat()
    monkeypatch.setattr(alttprladder, "get_racer_guid", mock.AsyncMock(return_value="g"))
    history = mock.AsyncMock(return_value=[{"Results": [{"StartDateTime": recent}, {"StartDateTime": old}]},
                                           {"Results": [{"StartDateTime": recent}]}])
    monkeypatch.setattr(alttprladder, "get_racer_history", history)
    assert await verification.get_ladder_count("runner", days=365) == 2
    history.assert_awaited_once_with("g")


@pytest.mark.parametrize(
    "use_ladder, ladder, archive, rtgg, expected",
    [
        (False, 0, 0, 2, (True, 2)),
        (False, 0, 0, 1, (False, 1)),
        (True, 1, 1, 0, (True, 2)),   # the ladder alone is enough: racetime.gg isn't asked
        (True, 1, 0, 3, (True, 4)),
    ],
)
async def test_determine_eligibility(monkeypatch, use_ladder, ladder, archive, rtgg, expected):
    monkeypatch.setattr(verification, "get_ladder_count", mock.AsyncMock(return_value=ladder))
    monkeypatch.setattr(verification, "get_ladder_archive_count", mock.AsyncMock(return_value=archive))
    rtgg_count = mock.AsyncMock(return_value=rtgg)
    monkeypatch.setattr(verification, "get_racetime_count", rtgg_count)
    user = SimpleNamespace(discord_user_id=5, rtgg_id="abc")
    rv = SimpleNamespace(racetime_categories="alttpr,smz3", use_alttpr_ladder=use_ladder,
                         minimum_races=2, time_period_days=30)

    assert await verification.determine_eligibility("runner", user, rv) == expected
    if ladder + archive >= 2:
        rtgg_count.assert_not_called()
    else:
        rtgg_count.assert_awaited_once_with("abc", ["alttpr", "smz3"], days=30, max_count=2)


async def test_verification_records(db):
    user = await models.Users.create(discord_user_id=5, rtgg_id="abc")
    assert await verification.get_linked_user(5) == user
    await models.Users.create(discord_user_id=6)
    assert await verification.get_linked_user(6) is None
    assert await verification.get_linked_user(7) is None

    rv = await verification.create_or_update(guild_id=1, role_id=2, minimum_races=3, racetime_categories="alttpr")
    again = await verification.create_or_update(guild_id=1, role_id=2, minimum_races=4, racetime_categories="alttpr")
    assert again.id == rv.id
    assert again.minimum_races == 4
    await verification.attach_message(again, message_id=10, channel_id=11)
    assert (await verification.get_for_message(10, 1)).id == rv.id
    assert await verification.get_for_message(10, 99) is None

    first = await verification.record_verified(user, again, 3)
    second = await verification.record_verified(user, again, 8)
    assert first.id == second.id
    assert (await models.VerifiedRacer.get(id=first.id)).estimated_count == 8


# ---------------------------------------------------------------------------
# Tournament results and rooms
# ---------------------------------------------------------------------------


def _finished_race(ended_at):
    return {
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": ended_at,
        "entrants": [
            {"place": 2, "user": {"name": "Second"}, "finish_time": "PT1H30M"},
            {"place": 1, "user": {"name": "First"}, "finish_time": "PT1H20M5S"},
        ],
    }


def test_result_row():
    race = SimpleNamespace(episode_id=42, srl_id="alttpr/room", permalink="https://alttpr.test/h/x", spoiler=None)
    now = datetime.datetime(2026, 1, 1, 2, 0, tzinfo=datetime.timezone.utc)
    row = tournament_results.result_row(race, _finished_race("2026-01-01T01:30:00+00:00"), stream_delay=10, now=now)
    assert row == [
        42, "2025-12-31 19:00:00", f"{config.RACETIME_URL}/alttpr/room", "First", "Second",
        "1:20:05", "1:30:00", "https://alttpr.test/h/x", None,
    ]
    # still inside the stream delay
    assert tournament_results.result_row(race, _finished_race("2026-01-01T01:55:00+00:00"), stream_delay=10, now=now) is None


def test_finish_time_of_a_forfeit_is_none():
    assert tournament_results.finish_time({"finish_time": None}) is None


async def test_create_tournament_race_room_skips_existing_live_room(db, fake_http, monkeypatch):
    bot = mock.Mock(http_uri=fake_http.url)
    event = mock.Mock()
    event.get_config = mock.AsyncMock(return_value=SimpleNamespace(data=SimpleNamespace(racetime_category="test")))
    event.construct_race_room = mock.AsyncMock(return_value={"name": "new"})
    monkeypatch.setitem(tournaments.TOURNAMENT_DATA, "evt", event)
    monkeypatch.setattr(bots, "_racetime_bots", {"test": bot})
    await models.TournamentResults.create(srl_id="test/old", episode_id="9", event="evt")

    fake_http.add("GET", "/test/old/data", body=json.dumps({"status": {"value": "open"}}))
    fake_http.add("GET", "/test/old/data", body=json.dumps({"status": {"value": "cancelled"}}))

    assert await tournament_jobs.create_tournament_race_room("evt", 9) is None  # room still open: leave it
    event.construct_race_room.assert_not_called()

    assert await tournament_jobs.create_tournament_race_room("evt", 9) == {"name": "new"}  # cancelled: replace it
    assert not await models.TournamentResults.filter(srl_id="test/old").exists()


def test_integrations_import_no_front_end_or_models():
    """The clients only talk HTTP: no Discord, racetime-bot, Quart or models."""
    import ast
    from pathlib import Path

    banned = ("discord", "racetime_bot", "quart", "alttprbot.models", "alttprbot_discord", "alttprbot_api", "alttprbot_racetime")
    for path in Path(__file__).resolve().parents[1].joinpath("alttprbot", "integrations").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                assert not any(name == b or name.startswith(b + ".") for b in banned), f"{path.name} imports {name}"


async def test_record_race_page_without_token_raises(racetime_site):
    racetime_site.add("GET", "/alttpr/room", body="<html>logged out</html>", content_type="text/html")
    with pytest.raises(racetime.RacetimeRecordError):
        await racetime.record_race({"url": "/alttpr/room", "recorded": False, "recordable": True})


@pytest.mark.parametrize("status, recorded, deleted", [("finished", True, False), ("cancelled", False, True), ("open", False, False)])
async def test_record_one_race(db, monkeypatch, status, recorded, deleted):
    race = await models.TournamentResults.create(srl_id="alttpr/room", episode_id="5", event="evt")
    race_data = {"status": {"value": status}, "url": "/alttpr/room", **_finished_race("2020-01-01T01:30:00+00:00")}
    monkeypatch.setattr(racetime, "get_race", mock.AsyncMock(return_value=race_data))
    record = mock.AsyncMock()
    monkeypatch.setattr(racetime, "record_race", record)
    wks = mock.Mock(append_row=mock.AsyncMock())

    await tournament_results._record_race(wks, race, SimpleNamespace(stream_delay=0, auto_record=True))

    assert wks.append_row.await_count == (1 if recorded else 0)
    assert record.await_count == (1 if recorded else 0)
    assert await models.TournamentResults.filter(srl_id="alttpr/room").exists() is not deleted
