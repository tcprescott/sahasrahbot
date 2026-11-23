"""Characterization tests for the Quart web app (alttprbot_api/).

Requests go through Quart's test client against the in-memory database.
Discord OAuth is faked: the ``login`` fixture decides who ``discord.fetch_user()``
returns (or raises Unauthorized), and the Discord bot is never connected, so
guild role lookups find nobody and only the AsyncTournamentPermissions rows
grant access.
"""

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from quart_discord import Unauthorized

from alttprbot import models
from alttprbot_api import api
from alttprbot_api.blueprints import ranked_choice
from alttprbot.services import asynctournament as service
from alttprbot_discord import gateways


@pytest.fixture
def client(db):
    return api.sahasrahbotapi.test_client()


@pytest.fixture
def login(monkeypatch):
    """Call ``login(discord_id)`` to sign in as that Discord user; ``login(None)`` signs out."""
    state = {"user": None}

    async def authorized():
        return state["user"] is not None

    async def fetch_user():
        if state["user"] is None:
            raise Unauthorized()
        return state["user"]

    monkeypatch.setattr(type(api.discord), "authorized", property(lambda self: authorized()))
    monkeypatch.setattr(api.discord, "fetch_user", fetch_user)

    def set_user(discord_id, name="tester"):
        state["user"] = None if discord_id is None else SimpleNamespace(
            id=discord_id, name=name, username=name, display_name=name, discriminator="0", avatar_url=""
        )
        return state["user"]

    return set_user


# ---------------------------------------------------------------------------
# App-level routes
# ---------------------------------------------------------------------------


async def test_robots_txt(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert await resp.get_data(as_text=True) == "User-agent: *\nDisallow: /\n"


async def test_index_renders_signed_out(client, login):
    resp = await client.get("/")
    assert resp.status_code == 200


async def test_me_redirects_to_login_when_signed_out(client, login):
    resp = await client.get("/me/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login/")


async def test_unknown_page_renders_not_found_page_with_status_200(client, login):
    resp = await client.get("/definitely-not-a-page")
    assert resp.status_code == 200  # the 404 handler doesn't set a status
    assert "The page you are looking for does not exist." in await resp.get_data(as_text=True)


async def test_healthcheck(client, monkeypatch):
    bot = api.discordbot
    monkeypatch.setattr(bot, "is_closed", lambda: False)
    monkeypatch.setattr(bot, "application_info", mock.AsyncMock(return_value=SimpleNamespace(owner=SimpleNamespace(id=1))))
    monkeypatch.setattr(bot, "fetch_user", mock.AsyncMock())
    resp = await client.get("/healthcheck")
    assert resp.status_code == 200
    assert await resp.get_json() == {"success": True}


async def test_healthcheck_when_discord_closed(client, login, monkeypatch):
    monkeypatch.setattr(api.discordbot, "is_closed", lambda: True)
    resp = await client.get("/healthcheck")
    assert "Something Bad Happened" in await resp.get_data(as_text=True)


async def test_purge_me_deletes_namespaces_and_verifications(client, login):
    login(42)
    await models.PresetNamespaces.create(name="mine", discord_user_id=42)
    await models.PresetNamespaces.create(name="theirs", discord_user_id=43)

    resp = await client.post("/purgeme", form={"confirmpurge": "no"})
    assert resp.headers["Location"].endswith("/me/")
    assert await models.PresetNamespaces.all().count() == 2

    resp = await client.post("/purgeme", form={"confirmpurge": "yes"})
    assert resp.headers["Location"].endswith("/logout/")
    assert await models.PresetNamespaces.all().values_list("name", flat=True) == ["theirs"]


# ---------------------------------------------------------------------------
# API key authorization (alttprbot_api/auth.py)
# ---------------------------------------------------------------------------


async def make_key(key="secret", type_="asynctournament", subtype=None):
    auth_key = await models.AuthorizationKeys.create(key=key, name="test")
    await models.AuthorizationKeyPermissions.create(auth_key=auth_key, type=type_, subtype=subtype)


@pytest.mark.parametrize("headers", [{}, {"Authorization": "wrong"}])
async def test_api_key_required(client, headers):
    await make_key()
    resp = await client.get("/async/api/tournaments", headers=headers)
    assert resp.status_code == 401


async def test_api_key_must_have_matching_type(client):
    await make_key(type_="something-else")
    resp = await client.get("/async/api/tournaments", headers={"Authorization": "secret"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Async tournament JSON API
# ---------------------------------------------------------------------------

AUTH = {"Authorization": "secret"}


async def make_async_tournament(active=True):
    tournament = await models.AsyncTournament.create(name="Async", guild_id=1, channel_id=2, owner_id=3, active=active)
    pool = await models.AsyncTournamentPermalinkPool.create(tournament=tournament, name="A")
    permalink = await models.AsyncTournamentPermalink.create(pool=pool, url="https://x/1")
    return tournament, pool, permalink


async def test_tournaments_api_lists_and_filters(client):
    await make_key()
    await make_async_tournament(active=True)
    await models.AsyncTournament.create(name="Old", guild_id=1, channel_id=9, owner_id=3, active=False)

    all_ = await (await client.get("/async/api/tournaments", headers=AUTH)).get_json()
    active = await (await client.get("/async/api/tournaments?active=true", headers=AUTH)).get_json()
    inactive = await (await client.get("/async/api/tournaments?active=false", headers=AUTH)).get_json()
    assert sorted(t["name"] for t in all_) == ["Async", "Old"]
    assert [t["name"] for t in active] == ["Async"]
    assert [t["name"] for t in inactive] == ["Old"]


async def test_tournament_api_detail_and_missing(client):
    await make_key()
    tournament, _, _ = await make_async_tournament()
    detail = await (await client.get(f"/async/api/tournaments/{tournament.id}", headers=AUTH)).get_json()
    assert detail["name"] == "Async"
    assert "races" not in detail and "permalink_pools" not in detail  # reverse relations excluded

    resp = await client.get("/async/api/tournaments/999", headers=AUTH)
    assert resp.status_code == 200  # not a 404
    assert await resp.get_json() == {"error": "Tournament not found."}


async def test_races_api_filters_and_paginates(client):
    await make_key()
    tournament, pool, permalink = await make_async_tournament()
    users = [await models.Users.create(display_name=f"u{i}", discord_user_id=i) for i in range(3)]
    for u in users:
        await models.AsyncTournamentRace.create(tournament=tournament, permalink=permalink, user=u, status="finished")
    await models.AsyncTournamentRace.create(tournament=tournament, permalink=permalink, user=users[0], status="forfeit")

    base = f"/async/api/tournaments/{tournament.id}/races"
    assert len(await (await client.get(base, headers=AUTH)).get_json()) == 4
    assert len(await (await client.get(base + "?status=forfeit", headers=AUTH)).get_json()) == 1
    assert len(await (await client.get(base + f"?user_id={users[0].id}", headers=AUTH)).get_json()) == 2
    assert len(await (await client.get(base + f"?pool_id={pool.id}", headers=AUTH)).get_json()) == 4
    page2 = await (await client.get(base + "?page=2&page_size=3", headers=AUTH)).get_json()
    assert len(page2) == 1

    resp = await client.get(base + "?page_size=101", headers=AUTH)
    assert resp.status_code == 400


async def test_pools_and_permalinks_api(client):
    await make_key()
    tournament, pool, permalink = await make_async_tournament()
    pools = await (await client.get(f"/async/api/tournaments/{tournament.id}/pools", headers=AUTH)).get_json()
    permalinks = await (await client.get(f"/async/api/tournaments/{tournament.id}/permalinks", headers=AUTH)).get_json()
    assert [p["name"] for p in pools] == ["A"]
    assert [p["url"] for p in permalinks] == ["https://x/1"]


async def test_leaderboard_api_shape(client):
    await make_key()
    tournament, pool, permalink = await make_async_tournament()
    user = await models.Users.create(display_name="runner", discord_user_id=5, rtgg_id="rt5", twitch_name="tv")
    from datetime import datetime, timedelta, timezone

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    race = await models.AsyncTournamentRace.create(
        tournament=tournament, permalink=permalink, user=user, status="finished",
        start_time=start, end_time=start + timedelta(hours=1, minutes=30), score=100.0,
    )

    (entry,) = await (await client.get(f"/async/api/tournaments/{tournament.id}/leaderboard", headers=AUTH)).get_json()
    assert entry["player"] == {"id": user.id, "display_name": "runner", "discord_user_id": 5, "twitch_name": "tv", "rtgg_id": "rt5"}
    assert entry["rank"] == 1 and entry["score"] == 100.0
    assert entry["counts"] == {"finished": 1, "forfeited": 0, "unplayed": 0}
    (r,) = entry["races"]
    assert (r["id"], r["elapsed_time"], r["status"], r["permalink_id"]) == (race.id, "01:30:00", "finished", permalink.id)


# ---------------------------------------------------------------------------
# Async tournament web pages: review queue, reviews, reattempts, public pages
# ---------------------------------------------------------------------------


async def setup_review(role="mod"):
    tournament, pool, permalink = await make_async_tournament()
    reviewer = await models.Users.create(display_name="reviewer", discord_user_id=100)
    runner = await models.Users.create(display_name="runner", discord_user_id=200)
    if role:
        await models.AsyncTournamentPermissions.create(tournament=tournament, user=reviewer, role=role)
    race = await models.AsyncTournamentRace.create(
        tournament=tournament, permalink=permalink, user=runner, status="finished", thread_id=12345
    )
    return tournament, reviewer, runner, race


async def test_is_async_tournament_user(db):
    tournament, reviewer, runner, _ = await setup_review(role="mod")
    assert await service.is_async_tournament_user(reviewer, tournament, ["admin", "mod"]) is True
    assert await service.is_async_tournament_user(runner, tournament, ["admin", "mod"]) is False
    assert await service.is_async_tournament_user(None, tournament, ["admin", "mod"]) is False
    assert await service.is_async_tournament_user(None, tournament, ["public"]) is False  # tournament is active
    tournament.active = False
    assert await service.is_async_tournament_user(None, tournament, ["public"]) is True


async def test_is_async_tournament_user_by_discord_role(db, monkeypatch):
    tournament, _, runner, _ = await setup_review(role=None)
    await models.AsyncTournamentPermissions.create(tournament=tournament, discord_role_id=777, role="mod")
    member = SimpleNamespace(roles=[SimpleNamespace(id=777)])
    monkeypatch.setattr(gateways.discordbot, "get_guild", lambda guild_id: SimpleNamespace(id=guild_id))
    monkeypatch.setattr(gateways.discord_members, "get_member", mock.AsyncMock(return_value=member))
    monkeypatch.setattr(service, "_member_role_lookup", gateways.member_role_ids)  # sahasrahbot.py registers this
    assert await service.is_async_tournament_user(runner, tournament, ["mod"]) is True


async def test_review_submit_saves_accepted(client, login):
    """The form posts "accepted" and it is stored verbatim. See
    test_asynctournament_scoring.test_known_issue_only_approved_ignores_runs_the_review_form_marks_accepted
    for why that matters."""
    tournament, reviewer, runner, race = await setup_review()
    login(100)
    resp = await client.post(
        f"/async/races/{tournament.id}/review/{race.id}", form={"review_status": "accepted", "reviewer_notes": "gg"}
    )
    assert resp.status_code == 302
    await race.refresh_from_db()
    assert (race.review_status, race.reviewer_notes, race.reviewed_by_id) == ("accepted", "gg", reviewer.id)
    assert race.reviewed_at is not None


async def test_review_submit_defaults_to_pending(client, login):
    tournament, _, _, race = await setup_review()
    login(100)
    await client.post(f"/async/races/{tournament.id}/review/{race.id}", form={})
    await race.refresh_from_db()
    assert race.review_status == "pending"


async def test_review_submit_rejections(client, login):
    tournament, reviewer, runner, race = await setup_review()

    login(200)  # the runner is not a mod
    assert (await client.post(f"/async/races/{tournament.id}/review/{race.id}", form={})).status_code == 403

    login(100)
    race.status = "in_progress"
    await race.save()
    assert (await client.post(f"/async/races/{tournament.id}/review/{race.id}", form={})).status_code == 403

    race.status = "finished"
    race.reattempted = True
    await race.save()
    assert (await client.post(f"/async/races/{tournament.id}/review/{race.id}", form={})).status_code == 403


async def test_mod_cannot_review_their_own_run(client, login):
    """Fixed in the async tournament service PR: the self-review guard used to compare
    an unfetched relation with a Users row, so a mod could accept their own run."""
    tournament, _, runner, race = await setup_review()
    await models.AsyncTournamentPermissions.create(tournament=tournament, user=runner, role="mod")
    login(200)
    resp = await client.post(f"/async/races/{tournament.id}/review/{race.id}", form={"review_status": "accepted"})
    assert resp.status_code == 403
    await race.refresh_from_db()
    assert (race.review_status, race.reviewed_by_id) == ("pending", None)


async def test_review_page_claims_unreviewed_run(client, login):
    tournament, reviewer, _, race = await setup_review()
    login(100)
    resp = await client.get(f"/async/races/{tournament.id}/review/{race.id}")
    assert resp.status_code == 200
    await race.refresh_from_db()
    assert race.reviewed_by_id == reviewer.id


async def test_review_page_does_not_claim_unfinished_run(client, login):
    tournament, _, _, race = await setup_review()
    race.status = "in_progress"
    await race.save()
    login(100)
    assert (await client.get(f"/async/races/{tournament.id}/review/{race.id}")).status_code == 200
    await race.refresh_from_db()
    assert race.reviewed_by_id is None


async def test_review_queue_requires_mod_and_filters(client, login):
    tournament, _, runner, race = await setup_review()
    live_run = await models.AsyncTournamentRace.create(
        tournament=tournament, permalink=race.permalink, user=runner, status="finished", thread_id=None
    )
    login(200)
    assert (await client.get(f"/async/races/{tournament.id}/queue")).status_code == 403

    login(100)
    resp = await client.get(f"/async/races/{tournament.id}/queue")
    assert resp.status_code == 200
    body = await resp.get_data(as_text=True)
    assert f"/review/{race.id}" in body  # finished, pending review, run in a Discord thread
    assert f"/review/{live_run.id}\"" not in body  # default live=false hides runs without a thread


async def test_reattempt_flow(client, login):
    tournament, _, runner, race = await setup_review()
    login(200)
    base = f"/async/races/{tournament.id}/reattempt"
    assert (await client.get(base)).status_code == 400  # no race_id
    assert (await client.get(f"{base}?race_id={race.id}")).status_code == 200

    resp = await client.post(f"/async/race/{tournament.id}/reattempt?race_id={race.id}", form={"reason": "crash"})
    assert resp.status_code == 302
    await race.refresh_from_db()
    assert (race.reattempted, race.reattempt_reason) == (True, "crash")

    # only one reattempt per tournament
    assert (await client.get(f"{base}?race_id={race.id}")).status_code == 403
    assert (await client.post(f"/async/race/{tournament.id}/reattempt?race_id={race.id}", form={})).status_code == 403


async def test_reattempt_someone_elses_race_is_forbidden(client, login):
    tournament, reviewer, _, race = await setup_review()
    login(100)
    assert (await client.get(f"/async/races/{tournament.id}/reattempt?race_id={race.id}")).status_code == 403


@pytest.mark.parametrize("path", ["leaderboard", "pools"])
async def test_public_pages_hidden_while_active(client, login, path):
    tournament, _, _, _ = await setup_review()
    prefix = "races" if path == "leaderboard" else "pools"
    url = f"/async/{prefix}/{tournament.id}" + ("/leaderboard" if path == "leaderboard" else "")
    assert (await client.get(url)).status_code == 403  # signed out, tournament active

    tournament.active = False
    await tournament.save()
    assert (await client.get(url)).status_code == 200

    tournament.active = True
    await tournament.save()
    login(100)  # mods can always see it
    assert (await client.get(url)).status_code == 200


async def test_permalink_page_for_live_race_skips_auth(client, login):
    tournament, _, _, race = await setup_review()
    permalink = await race.permalink
    assert (await client.get(f"/async/permalink/{tournament.id}/{permalink.id}")).status_code == 403
    permalink.live_race = True
    await permalink.save()
    assert (await client.get(f"/async/permalink/{tournament.id}/{permalink.id}")).status_code == 200


# ---------------------------------------------------------------------------
# Presets pages
# ---------------------------------------------------------------------------


async def test_presets_index_and_namespace_pages(client, login):
    ns = await models.PresetNamespaces.create(name="synack", discord_user_id=1)
    await models.Presets.create(namespace=ns, preset_name="mine", randomizer="alttpr", content="settings: {}")
    assert (await client.get("/presets")).status_code == 200
    resp = await client.get("/presets/manage/synack")
    assert resp.status_code == 200
    assert "mine" in await resp.get_data(as_text=True)


async def test_preset_create_requires_namespace_owner(client, login):
    await models.PresetNamespaces.create(name="synack", discord_user_id=1)
    login(2)
    resp = await client.post(
        "/presets/synack/create",
        form={"preset_name": "x", "randomizer": "alttpr"},
    )
    assert "not authorized to create presets" in await resp.get_data(as_text=True)
    assert not await models.Presets.exists()


async def test_preset_create_rejects_bad_names(client, login):
    await models.PresetNamespaces.create(name="synack", discord_user_id=1)
    login(1)
    resp = await client.post("/presets/synack/create", form={"preset_name": "bad name!", "randomizer": "alttpr"})
    assert "Invalid preset name provided." in await resp.get_data(as_text=True)


async def test_my_presets_creates_namespace_and_redirects(client, login):
    login(42, name="New User")
    resp = await client.get("/presets/me")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/presets/manage/new-user")
    assert await models.PresetNamespaces.get(discord_user_id=42)


# ---------------------------------------------------------------------------
# Triforce texts
# ---------------------------------------------------------------------------


async def test_triforce_text_submit_validates_lines(client, login):
    login(5)
    ok = await client.post("/triforcetexts/pool/submit", form={"first_line": "HELLO", "second_line": "", "third_line": "BYE"})
    assert ok.status_code == 200
    (text,) = await models.TriforceTexts.all()
    assert (text.text, text.discord_user_id, text.author, text.approved) == ("HELLO\n\nBYE", 5, "tester#0", None)

    too_long = await client.post(
        "/triforcetexts/pool/submit", form={"first_line": "x" * 20, "second_line": "", "third_line": ""}
    )
    assert "Invalid text entered for the first line." in await too_long.get_data(as_text=True)
    assert await models.TriforceTexts.all().count() == 1


async def test_triforce_text_moderation(client, login):
    await models.TriforceTextsConfig.create(pool_name="pool", key_name="moderator", value="7")
    text = await models.TriforceTexts.create(pool_name="pool", text="hi", discord_user_id=1)

    login(8)
    denied = await client.get(f"/triforcetexts/pool/moderation/{text.id}/approve")
    assert "You do not have permission" in await denied.get_data(as_text=True)
    await text.refresh_from_db()
    assert text.approved is None

    login(7)
    assert (await client.get("/triforcetexts/pool/moderation")).status_code == 200
    await client.get(f"/triforcetexts/pool/moderation/{text.id}/approve")
    await text.refresh_from_db()
    assert text.approved is True
    await client.get(f"/triforcetexts/pool/moderation/{text.id}/reject")
    await text.refresh_from_db()
    assert text.approved is False


# ---------------------------------------------------------------------------
# Ranked choice voting
# ---------------------------------------------------------------------------


def test_ranked_choice_helpers():
    assert ranked_choice.remove_prefix("candidate_12", "candidate_") == "12"
    assert ranked_choice.remove_prefix("other", "candidate_") == "other"
    assert ranked_choice.dupcheck(["1", "1"]) is True
    assert ranked_choice.dupcheck(["1", "2"]) is False


def test_known_issue_dupcheck_only_checks_first_element():
    """KNOWN ISSUE, pinned not endorsed: ``dupcheck`` returns inside the loop,
    so only the first element is checked. Duplicate ranks after the first slip
    through (the code comment says "this is broken and we're not sure why")."""
    assert ranked_choice.dupcheck(["1", "2", "2"]) is False
    assert ranked_choice.dupcheck([]) is None


async def test_ranked_choice_ballot_submission(client, login, monkeypatch):
    election = await models.RankedChoiceElection.create(owner_id=1, title="Best", seats=1, channel_id=1, message_id=1)
    a = await models.RankedChoiceCandidate.create(election=election, name="A")
    b = await models.RankedChoiceCandidate.create(election=election, name="B")
    published = []
    monkeypatch.setattr(ranked_choice.events, "publish", published.append)
    login(9)

    resp = await client.post(f"/ranked_choice/{election.id}", form={f"candidate_{a.id}": "2", f"candidate_{b.id}": "1"})
    assert resp.status_code == 200
    # The Discord post refresh is a subscriber's job (alttprbot_discord/notifications.py).
    assert published == [ranked_choice.events.RankedChoiceBallotCast(
        election_id=election.id, occurred_at=published[0].occurred_at)]
    votes = await models.RankedChoiceVotes.filter(user_id=9).order_by("rank").prefetch_related("candidate")
    assert [(v.candidate.name, v.rank) for v in votes] == [("B", 1), ("A", 2)]

    again = await client.post(f"/ranked_choice/{election.id}", form={f"candidate_{a.id}": "1"})
    assert again.status_code == 403  # one ballot per voter


async def test_ranked_choice_inactive_or_missing(client, login):
    """abort(404) goes through the app's 404 handler, which renders the error
    page with status 200 (the handler returns no status code)."""
    login(9)
    missing = await client.get("/ranked_choice/999")
    assert missing.status_code == 200
    assert "Not Found" in await missing.get_data(as_text=True)
    election = await models.RankedChoiceElection.create(owner_id=1, title="Old", active=False)
    assert "Not Found" in await (await client.get(f"/ranked_choice/{election.id}")).get_data(as_text=True)


# ---------------------------------------------------------------------------
# racetime command API
# ---------------------------------------------------------------------------


async def test_racetime_cmd_requires_key_for_category(client):
    await make_key(key="k", type_="racetimecmd", subtype="alttpr")
    payload = {"category": "smz3", "room": "r", "cmd": "!race open"}
    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 403
