"""The non-/api/v1 web routes: the racetime command API and racetime.gg account
linking (alttprbot_api/blueprints/racetime.py), public preset JSON
(presets.py), the mystery settings generator (settingsgen.py) and tournament
games (tournament.py).

Requests go through Quart's test client; racetime.gg OAuth is the ``fake_http``
server and Discord sign-in is the ``login`` fixture from ``tests/test_api.py``.
"""

import json
from types import SimpleNamespace
from unittest import mock

import pytest

import testdata
from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.services import accounts
from alttprbot.services import bots
from alttprbot_api import api  # noqa: F401  (import the app before its blueprints, as production does)
from alttprbot_api.blueprints import racetime as racetime_bp
from alttprbot_api.blueprints import settingsgen
from tests.test_api import client, login, make_key  # noqa: F401  (fixtures)

JSON = {"Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# POST /api/racetime/cmd
# ---------------------------------------------------------------------------


async def test_racetime_cmd_runs_command_as_monitor(client, monkeypatch):  # noqa: F811
    await make_key(key="k", subtype="alttpr")
    handler = mock.Mock(send_message=mock.AsyncMock(), chat_message=mock.AsyncMock())
    bot = SimpleNamespace(handlers={"alttpr/cool-room-1234": SimpleNamespace(handler=handler)})
    monkeypatch.setattr(bots, "_racetime_bots", {"alttpr": bot})
    payload = {"category": "alttpr", "room": "cool-room-1234", "cmd": "!race open"}

    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers=JSON)

    assert resp.status_code == 200
    assert await resp.get_json() == {"success": True}
    handler.send_message.assert_awaited_once_with("Executing command from API request: !race open")
    message = handler.chat_message.await_args.args[0]["message"]
    assert (message["message"], message["is_monitor"], message["user"]["can_moderate"]) == ("!race open", True, True)


async def test_racetime_cmd_unknown_category(client, monkeypatch):  # noqa: F811
    await make_key(key="k", subtype="ootr")
    monkeypatch.setattr(bots, "_racetime_bots", {})
    payload = {"category": "ootr", "room": "r", "cmd": "!x"}
    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers=JSON)
    assert resp.status_code == 404
    assert await resp.get_json() == {"error": "Invalid game category"}


async def test_racetime_cmd_wrong_permission_type(client):  # noqa: F811
    await make_key(key="k", type_="something-else", subtype="alttpr")
    payload = {"category": "alttpr", "room": "r", "cmd": "!x"}
    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers=JSON)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# racetime.gg account linking
# ---------------------------------------------------------------------------


async def test_verification_initiate_redirects_to_racetime(client, login, monkeypatch):  # noqa: F811
    monkeypatch.setattr(racetime_bp, "RACETIME_URL", "https://racetime.test")
    monkeypatch.setattr(racetime_bp, "RACETIME_CLIENT_ID_OAUTH", "client-id")
    monkeypatch.setattr(racetime_bp, "APP_URL", "https://app.test")
    login(1)

    resp = await client.get("/racetime/verification/initiate")

    assert resp.status_code == 302
    assert resp.headers["Location"] == (
        "https://racetime.test/o/authorize?client_id=client-id&response_type=code&scope=read"
        "&redirect_uri=https%3A//app.test/racetime/verify/return")


@pytest.fixture
def racetime_oauth(fake_http, monkeypatch):
    monkeypatch.setattr(racetime_bp, "RACETIME_URL", fake_http.url())
    fake_http.add("POST", "/o/token", body=json.dumps({"access_token": "tok"}))
    fake_http.add("GET", "/o/userinfo", body=json.dumps({"id": "rt-new", "name": "Runner#1234"}))
    return fake_http


async def test_verify_return_links_new_racetime_account(client, login, racetime_oauth):  # noqa: F811
    login(91000000000000001, name="alice")

    resp = await client.get("/racetime/verify/return?code=abc")

    assert resp.status_code == 302
    assert resp.headers["Location"] == "/me?racetime=Runner%231234"
    user = await models.Users.get(discord_user_id=91000000000000001)
    assert (user.rtgg_id, user.rtgg_access_token, user.display_name) == ("rt-new", "tok", "alice")
    token_request = racetime_oauth.requests[0]
    assert "code=abc" in token_request.body and "grant_type=authorization_code" in token_request.body
    assert racetime_oauth.requests[1].path == "/o/userinfo"


async def test_verify_return_attaches_discord_to_existing_racetime_user(client, login, racetime_oauth):  # noqa: F811
    existing = await models.Users.create(rtgg_id="rt-new", display_name="old")
    login(91000000000000002, name="bob")

    await client.get("/racetime/verify/return?code=abc")

    existing = await models.Users.get(id=existing.id)
    assert (existing.discord_user_id, existing.display_name) == (91000000000000002, "bob")
    assert await models.Users.all().count() == 1


async def test_verify_return_merges_two_users(client, login, racetime_oauth):  # noqa: F811
    rtgg_user = await models.Users.create(rtgg_id="rt-new", display_name="racetime side")
    discord_user = await models.Users.create(discord_user_id=91000000000000003, display_name="discord side")
    login(91000000000000003, name="carol")

    await client.get("/racetime/verify/return?code=abc")

    [kept] = await models.Users.all()
    assert kept.id == rtgg_user.id
    assert (kept.discord_user_id, kept.rtgg_id, kept.display_name) == (91000000000000003, "rt-new", "carol")
    assert not await models.Users.exists(id=discord_user.id)


async def test_verify_return_requires_code(client, login):  # noqa: F811
    login(1)
    resp = await client.get("/racetime/verify/return")
    # a page route, so the error goes to the web app's error page
    assert resp.headers["Location"] == "/error?code=400&message=code%20is%20missing"


async def test_merge_users_moves_async_tournament_rows(db):
    """The async tournament feature is gone but its rows stay; merging accounts still rewrites them."""
    await testdata.load("asynctournament")
    races = await models.AsyncTournamentRace.all().prefetch_related("user")
    victim = races[0].user
    victim_races = await models.AsyncTournamentRace.filter(user=victim).count()
    keeper = await models.Users.create(display_name="keeper", rtgg_id=None)
    keeper_races_before = await models.AsyncTournamentRace.filter(user=keeper).count()

    kept = await accounts.merge_users(keeper, victim)

    assert kept.discord_user_id == victim.discord_user_id
    assert not await models.Users.exists(id=victim.id)
    assert await models.AsyncTournamentRace.filter(user=keeper).count() == keeper_races_before + victim_races


# ---------------------------------------------------------------------------
# /presets/api
# ---------------------------------------------------------------------------


async def test_presets_api_list(client):  # noqa: F811
    namespace = await models.PresetNamespaces.create(name="synack", discord_user_id=1)
    await models.Presets.create(namespace=namespace, randomizer="alttpr", preset_name="mine", content="x: 1")
    await models.Presets.create(namespace=namespace, randomizer="smz3", preset_name="other", content="x: 1")
    await models.PresetNamespaces.create(name="empty", discord_user_id=2)

    resp = await client.get("/presets/api/alttpr/list")

    body = await resp.get_json()
    assert "open" in body["global"]
    assert body["namespaces"] == [{"name": "synack", "presets": ["mine"]}]


async def test_presets_api_get(client):  # noqa: F811
    found = await (await client.get("/presets/api/alttpr?preset=open")).get_json()
    assert (found["preset"], found["randomizer"]) == ("open", "alttpr")
    assert "mode: open" in found["data"]  # the preset file's YAML text

    assert await (await client.get("/presets/api/alttpr?preset=nope")).get_json() == {}


async def test_presets_api_get_broken_namespaced_preset(client):  # noqa: F811
    namespace = await models.PresetNamespaces.create(name="synack", discord_user_id=1)
    await models.Presets.create(namespace=namespace, randomizer="alttpr", preset_name="broken",
                                content='goal_name: "x"\n  goal: ganon\n')

    resp = await client.get("/presets/api/alttpr?preset=synack/broken")

    assert resp.status_code == 422
    assert "isn't valid YAML" in (await resp.get_json())["error"]


# ---------------------------------------------------------------------------
# /api/settingsgen/mystery
# ---------------------------------------------------------------------------


def mystery(customizer=False, doors=False):
    return SimpleNamespace(settings={"mode": "open"}, customizer=customizer, doors=doors, custom_instructions=None)


@pytest.mark.parametrize(
    "result, endpoint",
    [(mystery(), "/api/randomizer"), (mystery(customizer=True), "/api/customizer"), (mystery(doors=True), None)],
)
async def test_settingsgen_from_named_weightset(client, monkeypatch, result, endpoint):  # noqa: F811
    seen = []

    async def generate_test_game(self):
        seen.append(self.preset)
        return result

    monkeypatch.setattr(generator.ALTTPRMystery, "generate_test_game", generate_test_game)

    by_path = await (await client.get("/api/settingsgen/mystery/weighted")).get_json()
    by_query = await (await client.get("/api/settingsgen/mystery?weightset=weighted")).get_json()

    assert by_path == by_query == {"settings": {"mode": "open"}, "customizer": result.customizer,
                                   "doors": result.doors, "endpoint": endpoint}
    assert seen == ["weighted", "weighted"]


async def test_settingsgen_from_posted_weights(client, monkeypatch):  # noqa: F811
    received = []

    async def custom_from_dict(cls, weights, preset_name=None):
        received.append(weights)
        return SimpleNamespace(generate_test_game=mock.AsyncMock(return_value=mystery()))

    monkeypatch.setattr(settingsgen.generator.ALTTPRMystery, "custom_from_dict", classmethod(custom_from_dict))
    resp = await client.post("/api/settingsgen/mystery", data=json.dumps({"weights": {"mode": {"open": 1}}}),
                             headers=JSON)

    assert (await resp.get_json())["endpoint"] == "/api/randomizer"
    assert received == [{"weights": {"mode": {"open": 1}}}]


# ---------------------------------------------------------------------------
# /api/tournament/games
# ---------------------------------------------------------------------------


async def test_tournament_games_filters_by_query(client):  # noqa: F811
    await models.TournamentGames.create(episode_id=1, event="alttpr", game_number=1)
    await models.TournamentGames.create(episode_id=2, event="smz3", game_number=2)

    every = await (await client.get("/api/tournament/games")).get_json()
    alttpr = await (await client.get("/api/tournament/games?event=alttpr")).get_json()

    assert sorted(g["episode_id"] for g in every) == [1, 2]
    assert [g["episode_id"] for g in alttpr] == [1]
