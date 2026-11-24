"""Tests for the Quart web app (alttprbot_api/): the JSON API the React app uses
(/api/v1), the server-side sign-in and download routes, and serving the app.

Requests go through Quart's test client against the in-memory database.
Discord OAuth is faked: the ``login`` fixture decides who ``discord.fetch_user()``
returns (or raises Unauthorized), and the Discord bot is never connected.
"""

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from quart_discord import Unauthorized

from alttprbot import events, models
from alttprbot_api import api
from alttprbot_api.blueprints import app_api
from alttprbot.services import bots

CSRF = {app_api.CSRF_HEADER: app_api.CSRF_VALUE}


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

    async def token():
        return {"scope": state["scope"]}

    async def my_guilds():
        # What Discord's /users/@me/guilds says: the fake directory's servers they administer.
        from alttprbot.services import discord_directory
        directory = discord_directory._directory
        ids = directory.admin_guild_ids(state["user"].id) if hasattr(directory, "admin_guild_ids") else set()
        state["guild_calls"] += 1
        return [{"id": str(gid), "owner": False, "permissions": "8"} for gid in ids]

    monkeypatch.setattr(type(api.discord), "authorized", property(lambda self: authorized()))
    monkeypatch.setattr(api.discord, "fetch_user", fetch_user)
    monkeypatch.setattr(api.discord, "get_authorization_token", token)
    monkeypatch.setattr(api.discord, "revoke", lambda: state.update(user=None))
    monkeypatch.setattr(app_api, "_fetch_discord_guilds", my_guilds)
    monkeypatch.setattr(app_api, "_admin_guilds", {})

    def set_user(discord_id, name="tester", scope="identify guilds"):
        state["scope"] = scope
        state["guild_calls"] = 0
        state["user"] = None if discord_id is None else SimpleNamespace(
            id=discord_id, name=name, username=name, display_name=name, discriminator="0", avatar_url=""
        )
        return state["user"]

    set_user.state = state
    return set_user


async def get_json(client, path):
    resp = await client.get(path)
    return resp.status_code, await resp.get_json()


async def send_json(client, method, path, body=None, headers=CSRF):
    resp = await client.open(path, method=method, json=body, headers=headers)
    return resp.status_code, await resp.get_json()


# ---------------------------------------------------------------------------
# App-level routes
# ---------------------------------------------------------------------------


async def test_robots_txt(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert await resp.get_data(as_text=True) == "User-agent: *\nDisallow: /\n"


async def test_page_paths_serve_the_app(client, monkeypatch, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app-abc.js").write_text("console.log(1)")
    monkeypatch.setattr(api, "WEB_DIST", tmp_path)

    for path in ("/", "/presets/manage/synack", "/ranked_choice/4", "/definitely-not-a-page"):
        resp = await client.get(path)
        assert resp.status_code == 200, path
        assert "id=root" in await resp.get_data(as_text=True)

    asset = await client.get("/assets/app-abc.js")
    assert await asset.get_data(as_text=True) == "console.log(1)"
    assert asset.cache_control.immutable


async def test_page_paths_explain_an_unbuilt_app(client, monkeypatch, tmp_path):
    monkeypatch.setattr(api, "WEB_DIST", tmp_path / "missing")
    resp = await client.get("/presets")
    assert "hasn't been built" in await resp.get_data(as_text=True)


async def test_unknown_api_path_is_json_404(client):
    status, body = await get_json(client, "/api/v1/nope")
    assert status == 404
    assert "error" in body


async def test_healthcheck(client, monkeypatch):
    bot = SimpleNamespace(
        is_closed=lambda: False,
        application_info=mock.AsyncMock(return_value=SimpleNamespace(owner=SimpleNamespace(id=1))),
        fetch_user=mock.AsyncMock(),
    )
    monkeypatch.setattr(bots, "_discord_client", bot)  # sahasrahbot.py registers the real bot
    resp = await client.get("/healthcheck")
    assert resp.status_code == 200
    assert await resp.get_json() == {"success": True}


async def test_healthcheck_when_discord_closed(client, login, monkeypatch):
    monkeypatch.setattr(bots, "_discord_client", SimpleNamespace(is_closed=lambda: True))
    resp = await client.get("/healthcheck")
    assert resp.status_code == 500
    assert "error" in await resp.get_json()


async def test_login_remembers_a_same_site_next_path_only(client, monkeypatch):
    seen = []

    async def create_session(scope, data):
        seen.append(data["redirect"])
        return "redirected"

    monkeypatch.setattr(api.discord, "create_session", create_session)
    await client.get("/login/?next=/ranked_choice/4")
    await client.get("/login/?next=//evil.example/")
    await client.get("/login/?next=https://evil.example/")
    assert seen == ["/ranked_choice/4", "/", "/"]


async def test_openapi_schema_covers_only_the_app_api(client):
    schema = await (await client.get("/api/v1/openapi.json")).get_json()
    assert schema["paths"]
    assert all(path.startswith("/api/v1/") for path in schema["paths"])
    assert "/api/v1/presets/namespaces/{namespace}" in schema["paths"]
    assert "/api/v1/triforce-texts/{pool}/moderation/{text_id}" in schema["paths"]


# ---------------------------------------------------------------------------
# Session, profile, purge
# ---------------------------------------------------------------------------


async def test_session_is_null_when_signed_out(client, login):
    assert await get_json(client, "/api/v1/session") == (200, {"user": None})
    login(123456789012345678, name="synack")
    status, body = await get_json(client, "/api/v1/session")
    assert body["user"] == {"id": "123456789012345678", "name": "synack", "avatar_url": None}


async def test_me_needs_sign_in(client, login):
    status, body = await get_json(client, "/api/v1/me")
    assert status == 401


async def test_me_reports_links(client, login):
    login(42)
    await models.Users.create(discord_user_id=42, rtgg_id="abc")
    await models.PresetNamespaces.create(name="mine", discord_user_id=42)
    await models.TriforceTextsConfig.create(pool_name="pool", key_name="moderator", value="42")
    status, body = await get_json(client, "/api/v1/me")
    assert status == 200
    assert (body["racetime_linked"], body["racetime_id"], body["preset_namespace"]) == (True, "abc", "mine")
    assert body["moderated_triforce_pools"] == ["pool"]


async def test_changes_need_the_csrf_header(client, login):
    login(42)
    await models.PresetNamespaces.create(name="mine", discord_user_id=42)
    status, _ = await send_json(client, "POST", "/api/v1/me/purge", headers={})
    assert status == 403
    assert await models.PresetNamespaces.exists(name="mine")


async def test_purge_me_deletes_namespaces_and_signs_out(client, login):
    login(42)
    await models.PresetNamespaces.create(name="mine", discord_user_id=42)
    await models.PresetNamespaces.create(name="theirs", discord_user_id=43)

    resp = await client.post("/api/v1/me/purge", headers=CSRF)
    assert resp.status_code == 204
    assert await models.PresetNamespaces.all().values_list("name", flat=True) == ["theirs"]
    assert await get_json(client, "/api/v1/session") == (200, {"user": None})


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


async def make_namespace(name="synack", owner=1):
    ns = await models.PresetNamespaces.create(name=name, discord_user_id=owner)
    await models.Presets.create(namespace=ns, preset_name="mine", randomizer="alttpr", content="settings: {}")
    return ns


async def test_namespace_list_and_page(client, login):
    await make_namespace()
    await models.PresetNamespaces.create(name="empty", discord_user_id=2)
    status, body = await get_json(client, "/api/v1/presets/namespaces")
    assert body["namespaces"] == [{"name": "empty", "preset_count": 0}, {"name": "synack", "preset_count": 1}]

    status, body = await get_json(client, "/api/v1/presets/namespaces/synack")
    assert status == 200
    assert body["can_edit"] is False
    assert [(p["randomizer"], p["name"]) for p in body["presets"]] == [("alttpr", "mine")]

    login(1)
    assert (await get_json(client, "/api/v1/presets/namespaces/synack"))[1]["can_edit"] is True
    assert (await get_json(client, "/api/v1/presets/namespaces/nobody"))[0] == 404


async def test_preset_view_and_download(client, login):
    await make_namespace()
    status, body = await get_json(client, "/api/v1/presets/namespaces/synack/alttpr/mine")
    assert (status, body["content"], body["can_edit"]) == (200, "settings: {}", False)

    download = await client.get("/presets/download/synack/alttpr/mine")
    assert await download.get_data(as_text=True) == "settings: {}"
    assert (await client.get("/presets/download/synack/alttpr/nope")).status_code == 404


async def test_preset_save_requires_namespace_owner(client, login):
    await make_namespace()
    path = "/api/v1/presets/namespaces/synack/alttpr/new"
    assert (await send_json(client, "PUT", path, {"content": "x: 1"}))[0] == 401
    login(2)
    assert (await send_json(client, "PUT", path, {"content": "x: 1"}))[0] == 403
    assert not await models.Presets.exists(preset_name="new")


async def test_preset_save_creates_replaces_and_validates(client, login):
    await make_namespace()
    login(1)
    status, body = await send_json(client, "PUT", "/api/v1/presets/namespaces/synack/alttpr/new", {"content": "x: 1"})
    assert (status, body["content"]) == (200, "x: 1")
    await send_json(client, "PUT", "/api/v1/presets/namespaces/synack/alttpr/new", {"content": "x: 2"})
    assert (await models.Presets.get(preset_name="new")).content == "x: 2"

    bad_name = await send_json(client, "PUT", "/api/v1/presets/namespaces/synack/alttpr/bad%20name", {"content": "x"})
    bad_rando = await send_json(client, "PUT", "/api/v1/presets/namespaces/synack/zelda1/ok", {"content": "x"})
    empty = await send_json(client, "PUT", "/api/v1/presets/namespaces/synack/alttpr/ok", {"content": "  "})
    assert [r[0] for r in (bad_name, bad_rando, empty)] == [400, 400, 400]
    assert "letters, numbers and underscores" in bad_name[1]["error"]


async def test_preset_delete(client, login):
    await make_namespace()
    login(1)
    resp = await client.delete("/api/v1/presets/namespaces/synack/alttpr/mine", headers=CSRF)
    assert resp.status_code == 204
    assert not await models.Presets.exists()
    resp = await client.delete("/api/v1/presets/namespaces/synack/alttpr/mine", headers=CSRF)
    assert resp.status_code == 404


async def test_my_namespace_is_created_on_first_use(client, login):
    login(42, name="New User")
    assert await get_json(client, "/api/v1/presets/mine") == (200, {"namespace": "new-user"})
    assert await models.PresetNamespaces.get(discord_user_id=42)


# ---------------------------------------------------------------------------
# Triforce texts
# ---------------------------------------------------------------------------


async def test_triforce_text_submit_validates_lines(client, login):
    login(5)
    status, body = await send_json(client, "POST", "/api/v1/triforce-texts/pool/submissions",
                                   {"lines": ["HELLO", "", "BYE"]})
    assert (status, body["status"], body["lines"]) == (201, "pending", ["HELLO", "", "BYE"])
    (text,) = await models.TriforceTexts.all()
    assert (text.text, text.discord_user_id, text.author, text.approved) == ("HELLO\n\nBYE", 5, "tester#0", None)

    too_long = await send_json(client, "POST", "/api/v1/triforce-texts/pool/submissions", {"lines": ["x" * 20, "", ""]})
    assert too_long[0] == 400
    assert "first line" in too_long[1]["error"]
    blank = await send_json(client, "POST", "/api/v1/triforce-texts/pool/submissions", {"lines": ["", "", ""]})
    two_lines = await send_json(client, "POST", "/api/v1/triforce-texts/pool/submissions", {"lines": ["A", "B"]})
    assert (blank[0], two_lines[0]) == (400, 400)
    assert await models.TriforceTexts.all().count() == 1

    status, body = await get_json(client, "/api/v1/triforce-texts/pool")
    assert (body["is_moderator"], [t["lines"] for t in body["mine"]]) == (False, [["HELLO", "", "BYE"]])
    assert "author" not in body["mine"][0] or body["mine"][0]["author"] is None


async def test_triforce_text_moderation(client, login):
    await models.TriforceTextsConfig.create(pool_name="pool", key_name="moderator", value="7")
    text = await models.TriforceTexts.create(pool_name="pool", text="hi", discord_user_id=1, author="a#0")
    other_pool = await models.TriforceTexts.create(pool_name="other", text="no", discord_user_id=1)

    login(8)
    assert (await get_json(client, "/api/v1/triforce-texts/pool/moderation"))[0] == 403
    denied = await send_json(client, "POST", f"/api/v1/triforce-texts/pool/moderation/{text.id}", {"approved": True})
    assert denied[0] == 403

    login(7)
    status, body = await get_json(client, "/api/v1/triforce-texts/pool/moderation")
    assert [(t["id"], t["author"]) for t in body["texts"]] == [(text.id, "a#0")]
    status, body = await send_json(client, "POST", f"/api/v1/triforce-texts/pool/moderation/{text.id}",
                                   {"approved": True})
    assert (status, body["status"]) == (200, "approved")
    assert (await get_json(client, "/api/v1/triforce-texts/pool/moderation"))[1]["texts"] == []
    approved = await get_json(client, "/api/v1/triforce-texts/pool/moderation?status=approved")
    assert [t["id"] for t in approved[1]["texts"]] == [text.id]
    await send_json(client, "POST", f"/api/v1/triforce-texts/pool/moderation/{text.id}", {"approved": False})
    await text.refresh_from_db()
    assert text.approved is False

    # A moderator of one pool can't touch another pool's texts through it.
    cross = await send_json(client, "POST", f"/api/v1/triforce-texts/pool/moderation/{other_pool.id}",
                            {"approved": True})
    assert cross[0] == 404


# ---------------------------------------------------------------------------
# Elections (the service itself is tested in tests/test_elections.py)
# ---------------------------------------------------------------------------

ADMIN, VOTER, OUTSIDER = 7, 9, 11
GUILD = 5


async def make_election(directory, status="open", method="stv", **kwargs):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], members={VOTER: [77], 10: []})
    election = await models.RankedChoiceElection.create(
        owner_id=ADMIN, title="Best", seats=1, guild_id=GUILD, channel_id=300, message_id=1,
        status=status, active=status == "open", method=method, **kwargs)
    a = await models.RankedChoiceCandidate.create(election=election, name="A", position=0)
    b = await models.RankedChoiceCandidate.create(election=election, name="B", position=1)
    c = await models.RankedChoiceCandidate.create(election=election, name="C", position=2)
    return election, a, b, c


async def test_ballot_can_be_cast_and_changed(client, login, monkeypatch, directory):
    election, a, b, c = await make_election(directory)
    published = []
    monkeypatch.setattr(events, "publish", published.append)
    login(VOTER)

    status, body = await get_json(client, f"/api/v1/elections/{election.id}/ballot")
    assert (status, body["ballot"], body["guild_name"]) == (200, None, "Community")
    assert [x["name"] for x in body["candidates"]] == ["A", "B", "C"]

    status, body = await send_json(client, "PUT", f"/api/v1/elections/{election.id}/ballot", {"choices": [b.id, a.id]})
    assert (status, body["ballot"]) == (200, [b.id, a.id])
    assert body["voted_at"]
    # The Discord post refresh is a subscriber's job (alttprbot_discord/notifications.py).
    assert published == [events.ElectionBallotCast(election_id=election.id, occurred_at=published[0].occurred_at)]

    status, body = await send_json(client, "PUT", f"/api/v1/elections/{election.id}/ballot", {"choices": [c.id]})
    assert (status, body["ballot"]) == (200, [c.id])
    votes = await models.RankedChoiceVotes.filter(user_id=VOTER)
    assert [(v.candidate_id, v.rank) for v in votes] == [(c.id, 1)]


async def test_old_ranked_choice_routes_still_work(client, login, directory):
    election, a, b, c = await make_election(directory)
    login(VOTER)
    assert (await get_json(client, f"/api/v1/ranked-choice/{election.id}"))[0] == 200
    status, body = await send_json(client, "POST", f"/api/v1/ranked-choice/{election.id}/ballot",
                                   {"ranking": [b.id, a.id]})
    assert (status, body["ballot"]) == (200, [b.id, a.id])


async def test_bad_ballots_are_refused(client, login, directory):
    election, a, b, c = await make_election(directory)
    other, x, *_ = await make_election(directory)
    login(VOTER)
    path = f"/api/v1/elections/{election.id}/ballot"
    for choices in ([a.id, b.id, b.id], [], [x.id]):
        status, _ = await send_json(client, "PUT", path, {"choices": choices})
        assert status == 400, choices
    assert not await models.RankedChoiceVotes.exists()


async def test_closed_draft_or_missing_elections_take_no_ballots(client, login, directory):
    login(VOTER)
    assert (await get_json(client, "/api/v1/elections/999/ballot"))[0] == 404
    closed, *_ = await make_election(directory, status="closed")
    draft, *_ = await make_election(directory, status="draft")
    assert (await get_json(client, f"/api/v1/elections/{closed.id}/ballot"))[0] == 404
    assert (await get_json(client, f"/api/v1/elections/{draft.id}/ballot"))[0] == 404


async def test_only_server_members_with_the_role_vote(client, login, directory):
    election, *_ = await make_election(directory, private=True, voter_role_id=77)
    login(VOTER)
    assert (await get_json(client, f"/api/v1/elections/{election.id}/ballot"))[0] == 200
    login(10)  # a member without the role
    assert (await get_json(client, f"/api/v1/elections/{election.id}/ballot"))[0] == 403
    login(OUTSIDER)
    assert (await get_json(client, f"/api/v1/elections/{election.id}/ballot"))[0] == 403


async def test_admin_creates_posts_edits_and_closes(client, login, directory):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], channels=[(300, "#votes")], roles=[(77, "@Voters")])
    login(ADMIN)

    status, body = await get_json(client, "/api/v1/elections/servers")
    assert (status, body) == (200, {"servers": [{"id": str(GUILD), "name": "Community"}]})
    status, body = await get_json(client, f"/api/v1/elections/servers/{GUILD}")
    assert body == {"channels": [{"id": "300", "name": "#votes"}], "roles": [{"id": "77", "name": "@Voters"}]}

    form = {"guild_id": str(GUILD), "channel_id": "300", "title": "Committee", "candidates": ["A", "B", "C"],
            "method": "stv", "seats": 2, "voter_role_id": "77",
            "closes_at": "2099-01-01T20:00:00+00:00"}
    status, draft = await send_json(client, "POST", "/api/v1/elections", form)
    assert status == 201
    assert (draft["status"], draft["voter_role_id"], draft["guild_id"], draft["seats"]) == ("draft", "77", "5", 2)
    assert [c["name"] for c in draft["candidates"]] == ["A", "B", "C"]

    status, edited = await send_json(client, "PUT", f"/api/v1/elections/{draft['id']}", {**form, "title": "Committee 2027"})
    assert (status, edited["title"]) == (200, "Committee 2027")

    status, posted = await send_json(client, "POST", f"/api/v1/elections/{draft['id']}/publish", {})
    assert (status, posted["status"], posted["message_id"]) == (200, "open", "9001")

    status, body = await get_json(client, "/api/v1/elections")
    assert [(e["id"], e["status"], e["ballots"]) for e in body["elections"]] == [(draft["id"], "open", 0)]

    status, closed = await send_json(client, "POST", f"/api/v1/elections/{draft['id']}/close", {})
    assert (status, closed["status"], closed["locked"]) == (200, "closed", True)

    status, results = await get_json(client, f"/api/v1/elections/{draft['id']}/results")
    assert (status, results["tally"]["ballots"], results["tally"]["winners"]) == (200, 0, [])

    assert (await send_json(client, "DELETE", f"/api/v1/elections/{draft['id']}", None))[0] == 204
    assert (await get_json(client, f"/api/v1/elections/{draft['id']}"))[0] == 404


async def test_session_without_guilds_scope_is_signed_out(client, login):
    # Sessions from before sign-in asked for "guilds" sign in again once.
    login(ADMIN, scope="identify")
    assert (await get_json(client, "/api/v1/session"))[1] == {"user": None}
    assert login.state["user"] is None  # revoked
    login(ADMIN, scope=["identify", "guilds"])  # oauthlib may store it as a list
    assert (await get_json(client, "/api/v1/session"))[1]["user"]["id"] == str(ADMIN)


async def test_admin_servers_are_asked_of_discord_once(client, login, directory):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN])
    login(ADMIN)
    for _ in range(3):
        assert (await get_json(client, "/api/v1/elections/servers"))[1] == {"servers": [{"id": str(GUILD), "name": "Community"}]}
    assert (await get_json(client, "/api/v1/elections"))[0] == 200
    assert login.state["guild_calls"] == 1  # cached for a minute


async def test_fetch_discord_guilds_pages_and_waits_out_a_rate_limit(monkeypatch):
    from quart_discord import RateLimited
    pages = {0: [{"id": str(i)} for i in range(1, app_api.GUILD_PAGE + 1)], app_api.GUILD_PAGE: [{"id": "999"}]}
    calls = []

    async def request(route):
        calls.append(route)
        if len(calls) == 1:
            raise RateLimited({"retry_after": 0, "message": "slow down", "global": False}, {})
        return pages[int(route.rsplit("after=", 1)[1])]

    monkeypatch.setattr(api.discord, "request", request)
    guilds = await app_api._fetch_discord_guilds()
    assert len(guilds) == app_api.GUILD_PAGE + 1
    assert calls[-1].endswith(f"after={app_api.GUILD_PAGE}")


def test_admin_means_owner_or_the_administrator_permission():
    assert app_api._is_admin({"owner": True, "permissions": "0"})
    assert app_api._is_admin({"owner": False, "permissions": str(0x8 | 0x400)})
    assert not app_api._is_admin({"owner": False, "permissions": str(0x20)})
    assert not app_api._is_admin({})


async def test_non_admins_cant_manage(client, login, directory):
    election, *_ = await make_election(directory)
    login(VOTER)
    assert (await get_json(client, "/api/v1/elections/servers"))[1] == {"servers": []}
    assert (await get_json(client, "/api/v1/elections"))[1] == {"elections": []}
    assert (await get_json(client, f"/api/v1/elections/{election.id}"))[0] == 403
    assert (await get_json(client, f"/api/v1/elections/servers/{GUILD}"))[0] == 403
    assert (await send_json(client, "POST", f"/api/v1/elections/{election.id}/close", {}))[0] == 403
    form = {"guild_id": str(GUILD), "channel_id": "300", "title": "Mine", "candidates": ["A", "B"]}
    assert (await send_json(client, "POST", "/api/v1/elections", form))[0] == 403


async def test_bad_ids_in_the_form_are_refused(client, login, directory):
    directory.add_guild(GUILD, admins=[ADMIN])
    login(ADMIN)
    form = {"guild_id": "five", "channel_id": "300", "title": "X", "candidates": ["A", "B"]}
    status, body = await send_json(client, "POST", "/api/v1/elections", form)
    assert (status, body["error"]) == (400, "That server isn't a Discord id.")


async def test_results_are_public_but_only_after_close(client, directory):
    election, *_ = await make_election(directory)
    assert (await get_json(client, f"/api/v1/elections/{election.id}/results"))[0] == 403
    election.status, election.active = "closed", False
    await election.save()
    status, body = await get_json(client, f"/api/v1/elections/{election.id}/results")
    assert (status, body["tally"]["method"]) == (200, "stv")


# ---------------------------------------------------------------------------
# Tournament settings submission
# ---------------------------------------------------------------------------


async def test_submission_form_for_unknown_event_is_404(client, login):
    login(9)
    assert (await get_json(client, "/api/v1/tournaments/nope/submission-form"))[0] == 404


async def test_submission_form_and_submit(client, login, monkeypatch):
    from alttprbot.services import tournament_submissions

    processed = []

    class FakeTournament:
        submission_form = [{"key": "preset", "label": "Preset", "settings": {"open": "Open", "boots": "Boots"}}]
        versus = "a vs b"

        @classmethod
        async def get_config(cls):
            return cls()

        async def process_submission_form(self, payload, submitted_by):
            processed.append((payload, submitted_by))

    async def fetch(event, episode_id):
        return FakeTournament()

    monkeypatch.setitem(tournament_submissions.TOURNAMENT_DATA, "fake", FakeTournament)
    monkeypatch.setattr(tournament_submissions, "fetch_tournament_handler", fetch)
    login(9)

    status, body = await get_json(client, "/api/v1/tournaments/fake/submission-form")
    assert body["fields"] == [{"key": "preset", "label": "Preset", "options": [
        {"value": "open", "label": "Open"}, {"value": "boots", "label": "Boots"}]}]

    bad = await send_json(client, "POST", "/api/v1/tournaments/fake/submissions",
                          {"episode_id": 12, "settings": {"preset": "zzz"}})
    assert bad[0] == 400
    status, body = await send_json(client, "POST", "/api/v1/tournaments/fake/submissions",
                                   {"episode_id": 12, "settings": {"preset": "boots"}})
    assert (status, body["versus"]) == (200, "a vs b")
    assert processed == [({"preset": "boots", "event": "fake", "episodeid": "12"}, "tester#0")]


# ---------------------------------------------------------------------------
# racetime command API
# ---------------------------------------------------------------------------


async def make_key(key="secret", type_="racetimecmd", subtype=None):
    auth_key = await models.AuthorizationKeys.create(key=key, name="test")
    await models.AuthorizationKeyPermissions.create(auth_key=auth_key, type=type_, subtype=subtype)


async def test_racetime_cmd_requires_key_for_category(client):
    await make_key(key="k", type_="racetimecmd", subtype="alttpr")
    payload = {"category": "smz3", "room": "r", "cmd": "!race open"}
    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Triforce text characters
# ---------------------------------------------------------------------------


def test_triforce_lines_only_allow_the_games_characters():
    """The hyphen used to sit between "," and "…" in the character class, making a
    range that let almost anything through (é, ß, emoji)."""
    from alttprbot.services import triforce_texts

    for ok in ("HELLO-WORLD", "ゼルダ", "WHY? BECAUSE!", ""):
        assert triforce_texts.LINE.match(ok), ok
    for bad in ("café", "straße", "😀", "x" * 20):
        assert not triforce_texts.LINE.match(bad), bad


def test_triforce_characters_match_the_web_app():
    """web/src/triforce/rules.ts checks lines as you type; it must allow exactly
    what the server does."""
    import re
    from pathlib import Path

    from alttprbot.services import triforce_texts

    server = re.match(r"\^\[(.*)\]\{0,19\}\$", triforce_texts.LINE.pattern).group(1)
    rules = (Path(__file__).resolve().parent.parent / "web/src/triforce/rules.ts").read_text(encoding="utf-8")
    web = re.search(r"/\^\[(.*?)\]\*\$/u", rules).group(1)
    assert web == server


# --- API access page and AI client consent -----------------------------------


async def test_tokens_page_makes_lists_and_revokes(client, login):
    login(91000000000000001, "alice")
    status, made = await send_json(client, "POST", "/api/v1/tokens",
                                   {"name": "script", "read_only": False, "expires_in_days": 30})
    assert status == 201
    assert made["token"].startswith("sb_pat_")
    assert made["row"]["read_only"] is False

    status, body = await get_json(client, "/api/v1/tokens")
    assert status == 200
    assert [t["name"] for t in body["tokens"]] == ["script"]
    assert body["mcp_url"].endswith("/mcp")
    assert "token" not in body["tokens"][0]

    resp = await client.delete(f"/api/v1/tokens/{made['row']['id']}", headers=CSRF)
    assert resp.status_code == 204
    assert (await get_json(client, "/api/v1/tokens"))[1]["tokens"] == []
    status, body = await send_json(client, "DELETE", f"/api/v1/tokens/{made['row']['id']}")
    assert status == 404


async def test_tokens_page_needs_sign_in_and_the_csrf_header(client, login):
    assert (await client.get("/api/v1/tokens")).status_code == 401
    login(91000000000000001, "alice")
    status, _ = await send_json(client, "POST", "/api/v1/tokens", {"name": "x"}, headers={})
    assert status == 403
    status, body = await send_json(client, "POST", "/api/v1/tokens", {"name": "x", "expires_in_days": 7})
    assert status == 400


async def test_consent_screen_routes(client, login, monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    from alttprbot.services import api_tokens, mcp_auth
    monkeypatch.setattr(mcp_auth, "_pending", {})
    redirect = "https://claude.ai/api/mcp/auth_callback"
    await mcp_auth.register_client("c", "Claude", [redirect], ["authorization_code"], ["code"], mcp_auth.CLIENT_SCOPE)

    def begin():
        return mcp_auth.begin_authorization(mcp_auth.PendingAuthorization(
            client_id="c", redirect_uri=redirect, redirect_uri_provided_explicitly=True, code_challenge="x",
            state="s", resource=None))

    login(91000000000000001, "alice")
    txn = begin()
    status, body = await get_json(client, f"/api/v1/oauth/requests/{txn}")
    assert (status, body) == (200, {"client_name": "Claude", "redirect_target": "claude.ai"})
    status, body = await send_json(client, "POST", f"/api/v1/oauth/requests/{txn}/approve", {"allow_changes": True})
    assert status == 200
    code = parse_qs(urlsplit(body["redirect_url"]).query)["code"][0]
    stored = await mcp_auth.load_code("c", code)
    assert (stored.discord_user_id, stored.read_only) == (91000000000000001, False)
    assert (await get_json(client, f"/api/v1/oauth/requests/{txn}"))[0] == 404

    txn = begin()
    status, body = await send_json(client, "POST", f"/api/v1/oauth/requests/{txn}/deny")
    assert status == 200 and "error=access_denied" in body["redirect_url"]
    assert await api_tokens.list_for_user(91000000000000001) == []
