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

    monkeypatch.setattr(type(api.discord), "authorized", property(lambda self: authorized()))
    monkeypatch.setattr(api.discord, "fetch_user", fetch_user)
    monkeypatch.setattr(api.discord, "revoke", lambda: state.update(user=None))

    def set_user(discord_id, name="tester"):
        state["user"] = None if discord_id is None else SimpleNamespace(
            id=discord_id, name=name, username=name, display_name=name, discriminator="0", avatar_url=""
        )
        return state["user"]

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
# Ranked choice voting
# ---------------------------------------------------------------------------


async def make_election(**kwargs):
    election = await models.RankedChoiceElection.create(
        owner_id=1, title="Best", seats=1, channel_id=1, message_id=1, **kwargs)
    a = await models.RankedChoiceCandidate.create(election=election, name="A")
    b = await models.RankedChoiceCandidate.create(election=election, name="B")
    c = await models.RankedChoiceCandidate.create(election=election, name="C")
    return election, a, b, c


async def test_ranked_choice_ballot_submission(client, login, monkeypatch):
    election, a, b, c = await make_election()
    published = []
    monkeypatch.setattr(events, "publish", published.append)
    login(9)

    status, body = await get_json(client, f"/api/v1/ranked-choice/{election.id}")
    assert (status, body["ballot"], [x["name"] for x in body["candidates"]]) == (200, None, ["A", "B", "C"])

    status, body = await send_json(client, "POST", f"/api/v1/ranked-choice/{election.id}/ballot",
                                   {"ranking": [b.id, a.id]})
    assert (status, body["ballot"]) == (200, [b.id, a.id])
    # The Discord post refresh is a subscriber's job (alttprbot_discord/notifications.py).
    assert published == [events.RankedChoiceBallotCast(election_id=election.id, occurred_at=published[0].occurred_at)]
    votes = await models.RankedChoiceVotes.filter(user_id=9).order_by("rank").prefetch_related("candidate")
    assert [(v.candidate.name, v.rank) for v in votes] == [("B", 1), ("A", 2)]

    again = await send_json(client, "POST", f"/api/v1/ranked-choice/{election.id}/ballot", {"ranking": [a.id]})
    assert again[0] == 403  # one ballot per voter


async def test_ranked_choice_rejects_bad_ballots(client, login):
    """The old form's duplicate check only looked at the first rank (``dupcheck``
    returned inside its loop); a ranking is now a list of distinct candidate ids."""
    election, a, b, c = await make_election()
    other, x, *_ = await make_election()
    login(9)
    path = f"/api/v1/ranked-choice/{election.id}/ballot"
    for ranking in ([a.id, b.id, b.id], [], [x.id]):
        status, _ = await send_json(client, "POST", path, {"ranking": ranking})
        assert status == 400, ranking
    assert not await models.RankedChoiceVotes.exists()


async def test_ranked_choice_inactive_or_missing(client, login):
    login(9)
    assert (await get_json(client, "/api/v1/ranked-choice/999"))[0] == 404
    election = await models.RankedChoiceElection.create(owner_id=1, title="Old", active=False)
    assert (await get_json(client, f"/api/v1/ranked-choice/{election.id}"))[0] == 404


async def test_private_election_needs_the_voter_role(client, login, monkeypatch):
    election, *_ = await make_election(private=True, guild_id=5, voter_role_id=77)
    guild = SimpleNamespace(id=5)
    monkeypatch.setattr(bots, "_discord_client", SimpleNamespace(fetch_guild=mock.AsyncMock(return_value=guild)))
    members = {9: SimpleNamespace(roles=[SimpleNamespace(id=77)]), 10: SimpleNamespace(roles=[SimpleNamespace(id=1)])}

    async def get_member(g, user_id):
        return members.get(user_id)

    monkeypatch.setattr("alttprbot.util.discord_members.get_member", get_member)
    login(9)
    assert (await get_json(client, f"/api/v1/ranked-choice/{election.id}"))[0] == 200
    login(10)
    assert (await get_json(client, f"/api/v1/ranked-choice/{election.id}"))[0] == 403
    login(11)
    assert (await get_json(client, f"/api/v1/ranked-choice/{election.id}"))[0] == 403


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
