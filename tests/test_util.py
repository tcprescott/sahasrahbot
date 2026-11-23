"""Characterization tests for shared helpers: alttprbot/util/, SpeedGaming,
spoiler log upload and the tournament recording helpers in alttprbot/tournaments.py.

HTTP goes to a local fake server (the ``fake_http`` fixture); Discord objects are mocks.
"""

import gzip
import json
import random
import re
import string
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

import config
from alttprbot import models, tournaments
from alttprbot.services import bots
from alttprbot.alttprgen import generator, spoilers
from alttprbot.util import discord_members, helpers, http, rankedchoice, speedgaming, triforce_text

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def test_generate_random_string():
    s = helpers.generate_random_string(32)
    assert len(s) == 32
    assert set(s) <= set(string.ascii_letters + string.digits)
    assert helpers.generate_random_string(0) == ""


# ---------------------------------------------------------------------------
# discord_members (no privileged intents: cache, then REST / gateway query)
# ---------------------------------------------------------------------------


def http_error(cls=discord.HTTPException, status=500):
    return cls(mock.Mock(status=status, reason="x"), "boom")


async def test_get_member_prefers_cache():
    guild = mock.Mock(spec=discord.Guild)
    cached = object()
    guild.get_member.return_value = cached
    assert await discord_members.get_member(guild, "123") is cached
    guild.get_member.assert_called_once_with(123)
    guild.fetch_member.assert_not_called()


async def test_get_member_falls_back_to_rest():
    guild = mock.Mock(spec=discord.Guild)
    guild.get_member.return_value = None
    guild.fetch_member = mock.AsyncMock(return_value="fetched")
    assert await discord_members.get_member(guild, 123) == "fetched"


@pytest.mark.parametrize("error", [http_error(discord.NotFound, 404), http_error()])
async def test_get_member_returns_none_on_http_errors(error):
    guild = mock.Mock(spec=discord.Guild, id=1)
    guild.get_member.return_value = None
    guild.fetch_member = mock.AsyncMock(side_effect=error)
    assert await discord_members.get_member(guild, 123) is None


async def test_get_member_none_inputs():
    assert await discord_members.get_member(None, 1) is None
    assert await discord_members.get_member(mock.Mock(), None) is None


def member(name, global_name=None, nick=None, discriminator="0"):
    return SimpleNamespace(name=name, global_name=global_name, nick=nick, discriminator=discriminator)


async def test_get_member_named_uses_cache_then_query():
    guild = mock.Mock(spec=discord.Guild, id=1)
    guild.get_member_named.return_value = None
    alice = member("alice", global_name="Alice A")
    guild.query_members = mock.AsyncMock(return_value=[member("alicia"), alice])

    assert await discord_members.get_member_named(guild, "alice") is alice
    guild.query_members.assert_awaited_once_with(query="alice", limit=100, cache=False)

    assert await discord_members.get_member_named(guild, "Alice A") is alice  # global name matches too


async def test_get_member_named_with_legacy_discriminator():
    guild = mock.Mock(spec=discord.Guild, id=1)
    guild.get_member_named.return_value = None
    old = member("bob", discriminator="1234")
    guild.query_members = mock.AsyncMock(return_value=[member("bob", discriminator="9999"), old])
    assert await discord_members.get_member_named(guild, "bob#1234") is old
    assert guild.query_members.call_args.kwargs["query"] == "bob"


async def test_get_member_named_errors_and_empty_inputs():
    guild = mock.Mock(spec=discord.Guild, id=1)
    guild.get_member_named.return_value = None
    guild.query_members = mock.AsyncMock(side_effect=TimeoutError())
    assert await discord_members.get_member_named(guild, "x") is None
    assert await discord_members.get_member_named(None, "x") is None
    assert await discord_members.get_member_named(guild, "") is None


# ---------------------------------------------------------------------------
# triforce_text
# ---------------------------------------------------------------------------


async def test_triforce_text_pools(db):
    assert await triforce_text.get_triforce_text_random("pool") is None
    assert await triforce_text.get_triforce_text_balanced("pool") is None

    await models.TriforceTexts.create(pool_name="pool", text="approved one", discord_user_id=1, approved=True)
    await models.TriforceTexts.create(pool_name="pool", text="not approved", discord_user_id=2, approved=False)
    await models.TriforceTexts.create(pool_name="pool", text="unreviewed", discord_user_id=3, approved=None)
    await models.TriforceTexts.create(pool_name="other", text="other pool", discord_user_id=1, approved=True)

    for _ in range(10):
        assert await triforce_text.get_triforce_text_random("pool") == "approved one"
        assert await triforce_text.get_triforce_text_balanced("pool") == "approved one"


async def test_triforce_text_balanced_picks_author_first(db):
    random.seed(0)
    for i in range(20):
        await models.TriforceTexts.create(pool_name="p", text=f"prolific {i}", discord_user_id=1, approved=True)
    await models.TriforceTexts.create(pool_name="p", text="rare", discord_user_id=2, approved=True)
    picks = [await triforce_text.get_triforce_text_balanced("p") for _ in range(200)]
    # one of two authors is picked evenly, so "rare" comes up about half the time
    assert 60 < picks.count("rare") < 140


async def test_generate_with_triforce_text(db, monkeypatch):
    gen = mock.AsyncMock(return_value="seed")
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", gen)
    seen = {}

    async def capture(self, **kwargs):
        seen["settings"] = self.preset_data["settings"]
        return await gen(**kwargs)

    monkeypatch.setattr(generator.ALTTPRPreset, "generate", capture)
    await models.TriforceTexts.create(pool_name="p", text="hello", discord_user_id=1, approved=True)

    assert await triforce_text.generate_with_triforce_text("p", "open", settings={"mode": "inverted"}, branch="tournament") == "seed"
    assert seen["settings"]["texts"] == {"end_triforce": "{NOBORDER}\nhello"}
    assert seen["settings"]["mode"] == "inverted"
    assert gen.call_args.kwargs == {
        "allow_quickswap": True,
        "tournament": True,
        "hints": False,
        "spoilers": "off",
        "branch": "tournament",
    }


# ---------------------------------------------------------------------------
# rankedchoice
# ---------------------------------------------------------------------------


async def test_ranked_choice_calculate_results(db):
    election = await models.RankedChoiceElection.create(owner_id=1, title="Best", seats=1)
    a, b, c = [await models.RankedChoiceCandidate.create(election=election, name=n) for n in "ABC"]
    ballots = {10: [a, b], 11: [a], 12: [b, a], 13: [c, b], 14: [b]}
    for voter, ranking in ballots.items():
        for rank, candidate in enumerate(ranking, start=1):
            await models.RankedChoiceVotes.create(election=election, user_id=voter, candidate=candidate, rank=rank)

    await rankedchoice.calculate_results(election)

    await election.refresh_from_db()
    winners = await models.RankedChoiceCandidate.filter(election=election, winner=True).values_list("name", flat=True)
    assert winners == ["B"]  # C is eliminated, its ballot moves to B: B 3 vs A 2
    assert "B" in election.results


async def test_ranked_choice_embed(db):
    election = await models.RankedChoiceElection.create(
        id=7, owner_id=1, title="Best", description="d", seats=2, private=True, voter_role_id=55, active=False
    )
    await models.RankedChoiceCandidate.create(election=election, name="A", winner=True)
    await models.RankedChoiceCandidate.create(election=election, name="B")
    await election.fetch_related("candidates")

    fields = {f.name: f.value for f in rankedchoice.create_embed(election).fields}
    assert fields["Candidates"] == "1. A ✅\n2. B "
    assert fields["Authorized Voters Role"] == "<@&55>"
    assert fields["Vote URL"] == f"{config.APP_URL}/ranked_choice/7"
    assert fields["Status"] == "Closed"


# ---------------------------------------------------------------------------
# http
# ---------------------------------------------------------------------------


async def test_request_generic_return_types(fake_http):
    fake_http.add("GET", "/x", body='{"a": 1}')
    url = fake_http.url("/x")
    assert await http.request_generic(url) == '{"a": 1}'
    assert await http.request_generic(url, returntype="json") == {"a": 1}
    assert await http.request_generic(url, returntype="binary") == b'{"a": 1}'
    assert await http.request_generic(url, returntype="yaml") == {"a": 1}
    await http.request_generic(url, reqparams={"q": "1"})
    assert fake_http.requests[-1].query == {"q": "1"}


async def test_request_json_post_and_put(fake_http):
    fake_http.add("POST", "/p", body='{"ok": true}')
    fake_http.add("PUT", "/p", body="done")
    assert await http.request_json_post(fake_http.url("/p"), {"x": 1}, returntype="json") == {"ok": True}
    assert await http.request_json_put(fake_http.url("/p"), {"x": 1}) == "done"
    assert [json.loads(r.body) for r in fake_http.requests] == [{"x": 1}, {"x": 1}]


async def test_request_generic_raises_for_status(fake_http):
    import aiohttp

    fake_http.add("GET", "/x", status=500)
    with pytest.raises(aiohttp.ClientResponseError):
        await http.request_generic(fake_http.url("/x"))


# ---------------------------------------------------------------------------
# SpeedGaming
# ---------------------------------------------------------------------------


@pytest.fixture
def sg_api(fake_http, monkeypatch):
    monkeypatch.setattr(config, "DEBUG", False)
    monkeypatch.setattr(config, "SG_API_ENDPOINT", fake_http.url("/api"))
    return fake_http


async def test_get_upcoming_episodes_by_event_queries_window(sg_api):
    from datetime import datetime, timezone

    sg_api.add("GET", "/api/schedule", body=json.dumps([{"id": 1}, {"id": 2}]), content_type="text/html")
    result = await speedgaming.get_upcoming_episodes_by_event(
        "alttpr", hours_past=1, hours_future=2, static_time=datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    )
    assert result == [{"id": 1}, {"id": 2}]
    assert sg_api.requests[0].query == {
        "event": "alttpr",
        "from": "2024-01-01T11:00:00+00:00",
        "to": "2024-01-01T14:00:00+00:00",
    }


async def test_known_issue_schedule_error_payload_is_not_a_list(sg_api):
    """KNOWN ISSUE, pinned not endorsed: when SpeedGaming returns
    ``{"error": ...}``, the logging line indexes it like a list of episodes and
    raises TypeError before the SGEventNotFoundException check is reached."""
    sg_api.add("GET", "/api/schedule", body=json.dumps({"error": "no event"}), content_type="text/html")
    with pytest.raises(TypeError):
        await speedgaming.get_upcoming_episodes_by_event("nope")


async def test_get_episode(sg_api):
    sg_api.add("GET", "/api/episode", body=json.dumps({"id": 5, "match1": {}}), content_type="text/html")
    sg_api.add("GET", "/api/episode", body=json.dumps({"error": "Failed to find episode"}), content_type="text/html")
    assert await speedgaming.get_episode(5) == {"id": 5, "match1": {}}
    assert sg_api.requests[0].query == {"id": "5"}
    with pytest.raises(speedgaming.SGEpisodeNotFoundException, match="Failed to find episode"):
        await speedgaming.get_episode(6)


async def test_get_episode_debug_fixture_zero_is_not_found(monkeypatch):
    monkeypatch.setattr(config, "DEBUG", True)
    with pytest.raises(speedgaming.SGEpisodeNotFoundException):
        await speedgaming.get_episode(0)


def test_known_issue_legacy_speedgaming_module_cannot_be_imported():
    """KNOWN ISSUE, pinned not endorsed: ``alttprbot/speedgaming.py`` (the older
    dataclass client) does ``from dataclasses_json import config`` and then
    ``import config``, so the field metadata calls the settings module and the
    import fails. Nothing imports it; ``alttprbot/util/speedgaming.py`` is the live one."""
    import importlib
    import sys

    sys.modules.pop("alttprbot.speedgaming", None)
    with pytest.raises(TypeError, match="not callable"):
        importlib.import_module("alttprbot.speedgaming")
    sys.modules.pop("alttprbot.speedgaming", None)


# ---------------------------------------------------------------------------
# Spoiler logs
# ---------------------------------------------------------------------------


async def test_write_json_to_disk_uploads_gzipped_spoiler(monkeypatch):
    seed = SimpleNamespace(hash="H1", code=["Big Key", "Bow"], get_formatted_spoiler=mock.Mock(return_value={"a": 1}))
    s3 = mock.AsyncMock()
    session = mock.Mock()
    session.client.return_value.__aenter__ = mock.AsyncMock(return_value=s3)
    session.client.return_value.__aexit__ = mock.AsyncMock(return_value=False)
    monkeypatch.setattr(spoilers.aioboto3, "Session", lambda: session)
    monkeypatch.setattr(config, "SPOILERLOGURLBASE", "https://spoilers.test")
    monkeypatch.setattr(config, "AWS_SPOILER_BUCKET_NAME", "bucket")

    url = await spoilers.write_json_to_disk(seed)

    kwargs = s3.put_object.call_args.kwargs
    assert re.fullmatch(r"spoiler__H1__BigKey-Bow__[A-Za-z0-9]{4}\.txt", kwargs["Key"])
    assert url == f"https://spoilers.test/{kwargs['Key']}"
    assert json.loads(gzip.decompress(kwargs["Body"])) == {"a": 1}
    assert (kwargs["Bucket"], kwargs["ACL"], kwargs["ContentEncoding"]) == ("bucket", "public-read", "gzip")
    seed.get_formatted_spoiler.assert_called_once_with(translate_dungeon_items=True)


async def test_generate_spoiler_game_requests_spoiler_generation(db, monkeypatch):
    seed = SimpleNamespace(url="u")
    gen = mock.AsyncMock(return_value=seed)
    monkeypatch.setattr(spoilers.ALTTPRPreset, "generate", gen)
    monkeypatch.setattr(spoilers, "write_json_to_disk", mock.AsyncMock(return_value="https://spoilers.test/x"))

    game = await spoilers.generate_spoiler_game("open", festive=True, branch="beeta", allow_quickswap=False)
    assert game.spoiler_log_url == "https://spoilers.test/x"
    assert game.seed is seed
    assert gen.call_args.kwargs == {
        "spoilers": "generate", "tournament": True, "allow_quickswap": False, "endpoint_prefix": "/festive", "branch": "beeta",
    }


# ---------------------------------------------------------------------------
# alttprbot.tournaments (racetime recording helpers)
# ---------------------------------------------------------------------------


def test_tournament_data_in_debug_is_test_only():
    assert set(tournaments.TOURNAMENT_DATA) == {"test"}  # config.example.py has DEBUG = True


@pytest.fixture
def racetime_site(fake_http, monkeypatch):
    monkeypatch.setattr(tournaments, "RACETIME_URL", fake_http.url())
    return fake_http


@pytest.mark.parametrize(
    "race_data",
    [{"url": "/r", "recorded": True, "recordable": True}, {"url": "/r", "recorded": False, "recordable": False}, {"url": "/r"}],
)
async def test_racetime_auto_record_skips_recorded_or_unrecordable(racetime_site, race_data):
    await tournaments.racetime_auto_record(race_data)
    assert racetime_site.requests == []


async def test_racetime_auto_record_posts_with_csrf_token(racetime_site):
    racetime_site.add("GET", "/alttpr/room", body='<form><input name="csrfmiddlewaretoken" value="tok"></form>', content_type="text/html")
    racetime_site.add("POST", "/alttpr/room/monitor/record")
    await tournaments.racetime_auto_record({"url": "/alttpr/room", "recorded": False, "recordable": True})
    assert [(r.method, r.path) for r in racetime_site.requests] == [("GET", "/alttpr/room"), ("POST", "/alttpr/room/monitor/record")]
    assert racetime_site.requests[1].body == "csrfmiddlewaretoken=tok"


async def test_racetime_auto_record_without_token_page_raises(racetime_site):
    racetime_site.add("GET", "/alttpr/room", status=403)
    with pytest.raises(Exception, match="Unable to acquire CSRF token"):
        await tournaments.racetime_auto_record({"url": "/alttpr/room", "recorded": False, "recordable": True})


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

    assert await tournaments.create_tournament_race_room("evt", 9) is None  # room still open: leave it
    event.construct_race_room.assert_not_called()

    assert await tournaments.create_tournament_race_room("evt", 9) == {"name": "new"}  # cancelled: replace it
    assert not await models.TournamentResults.filter(srl_id="test/old").exists()
