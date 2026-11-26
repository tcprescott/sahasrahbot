"""Tests for the MCP server (alttprbot_api/mcp/) and for personal access tokens on
/api/v1: an AI client registers, the person approves it on the consent screen, the
client trades the code for tokens and calls tools, all through the Quart app.
"""

import base64
import hashlib
import secrets
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.services import api_tokens, mcp_auth, presets
from alttprbot_api import api
from alttprbot_api.mcp import oauth, registry

ALICE = 91000000000000001
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
WRITE_TOOLS = {
    "save_preset", "delete_preset", "cast_ballot", "create_election", "update_election", "publish_election",
    "close_election", "delete_election", "submit_triforce_text", "moderate_triforce_text",
    "submit_tournament_settings", "create_role_menu", "update_role_menu", "delete_role_menu",
}


@pytest.fixture
async def client(db, monkeypatch):
    monkeypatch.setattr(mcp_auth, "_pending", {})
    monkeypatch.setattr(oauth, "_hits", oauth.defaultdict(oauth.deque))
    app = api.sahasrahbotapi
    await app.startup()
    try:
        yield app.test_client()
    finally:
        await app.shutdown()


async def connect(client, allow_changes=False):
    """Run the OAuth flow as Claude would; returns the token response."""
    resp = await client.post("/register", json={
        "client_name": "Claude", "redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"]})
    assert resp.status_code == 201
    client_id = (await resp.get_json())["client_id"]
    verifier = secrets.token_urlsafe(40)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    resp = await client.get("/authorize", query_string={
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT, "code_challenge": challenge,
        "code_challenge_method": "S256", "state": "xyz", "scope": mcp_auth.CLIENT_SCOPE})
    assert resp.status_code == 302
    consent = urlsplit(resp.headers["location"])
    assert consent.path == "/oauth/consent"
    txn = parse_qs(consent.query)["txn"][0]
    back = await mcp_auth.approve(txn, ALICE, "alice", allow_changes)
    code = parse_qs(urlsplit(back).query)["code"][0]
    resp = await client.post("/token", form={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "client_id": client_id,
        "code_verifier": verifier})
    assert resp.status_code == 200, await resp.get_data()
    return {**await resp.get_json(), "client_id": client_id}


def headers(access_token):
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-06-18"}


async def rpc(client, token, method, params=None):
    resp = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
                             headers=headers(token))
    assert resp.status_code == 200, await resp.get_data()
    return (await resp.get_json())["result"]


async def call(client, token, tool, **arguments):
    return await rpc(client, token, "tools/call", {"name": tool, "arguments": arguments})


# --- Discovery and sign-in ----------------------------------------------------


async def test_metadata_documents(client):
    resp = await client.get("/.well-known/oauth-protected-resource/mcp")
    body = await resp.get_json()
    assert body["resource"].endswith("/mcp")
    assert body["scopes_supported"] == [mcp_auth.READ_SCOPE, mcp_auth.WRITE_SCOPE]
    resp = await client.get("/.well-known/oauth-authorization-server")
    meta = await resp.get_json()
    assert meta["authorization_endpoint"].endswith("/authorize")
    assert meta["registration_endpoint"].endswith("/register")
    assert "S256" in meta["code_challenge_methods_supported"]


async def test_mcp_without_a_token_gets_a_challenge(client):
    resp = await client.post("/mcp", json={})
    assert resp.status_code == 401
    assert 'resource_metadata="' in resp.headers["www-authenticate"]


async def test_mcp_refuses_a_personal_token(client):
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", False, None)
    resp = await client.post("/mcp", json={}, headers=headers(raw))
    assert resp.status_code == 401
    assert "Personal access tokens are for the REST API" in (await resp.get_json())["error_description"]


async def test_mcp_refuses_a_bad_token(client):
    resp = await client.post("/mcp", json={}, headers=headers("sb_mcp_nope"))
    assert resp.status_code == 401
    assert "invalid, expired or revoked" in (await resp.get_json())["error_description"]


async def test_register_refuses_a_script_redirect(client):
    resp = await client.post("/register", json={"client_name": "x", "redirect_uris": ["javascript:alert(1)"],
                                                "token_endpoint_auth_method": "none"})
    assert resp.status_code == 400


async def test_oauth_routes_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(oauth, "RATE_LIMIT", 2)
    codes = [(await client.get("/.well-known/oauth-authorization-server")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


async def test_refresh_rotates_and_the_old_token_stops_working(client):
    tokens = await connect(client)
    resp = await client.post("/token", form={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"],
                                             "client_id": tokens["client_id"]})
    fresh = await resp.get_json()
    assert resp.status_code == 200
    assert fresh["access_token"] != tokens["access_token"]
    assert (await client.post("/mcp", json={}, headers=headers(tokens["access_token"]))).status_code == 401
    assert (await rpc(client, fresh["access_token"], "tools/list"))["tools"]


async def test_disconnecting_on_the_website_ends_the_connection(client):
    tokens = await connect(client)
    [row] = await api_tokens.list_for_user(ALICE)
    await api_tokens.revoke(row["id"], ALICE)
    assert (await client.post("/mcp", json={}, headers=headers(tokens["access_token"]))).status_code == 401


# --- Tools ------------------------------------------------------------------------


async def test_every_tool_is_registered_with_a_spec(client):
    tokens = await connect(client, allow_changes=True)
    listed = {t["name"]: t for t in (await rpc(client, tokens["access_token"], "tools/list"))["tools"]}
    assert set(listed) == set(registry.TOOL_SPECS)
    assert registry.write_tool_names() == WRITE_TOOLS
    for name, tool in listed.items():
        assert tool["annotations"]["readOnlyHint"] is (name not in WRITE_TOOLS), name
        assert tool["description"], name
    assert listed["roll_seed"]["annotations"]["openWorldHint"] is True
    assert listed["delete_election"]["annotations"]["destructiveHint"] is True


async def test_read_only_connection_hides_and_refuses_writes(client):
    tokens = await connect(client)
    names = {t["name"] for t in (await rpc(client, tokens["access_token"], "tools/list"))["tools"]}
    assert names == set(registry.TOOL_SPECS) - WRITE_TOOLS
    result = await call(client, tokens["access_token"], "save_preset", namespace="alice", randomizer="alttpr",
                        preset="mine", content="settings: {}")
    assert result["isError"] is True
    assert "read_only:" in result["content"][0]["text"]


async def test_whoami(client):
    tokens = await connect(client)
    result = await call(client, tokens["access_token"], "whoami")
    assert result["structuredContent"] == {"discord_user_id": str(ALICE), "name": "alice", "can_make_changes": False}


async def test_write_connection_saves_a_preset(client):
    namespace = await presets.my_namespace(ALICE, "alice")
    tokens = await connect(client, allow_changes=True)
    result = await call(client, tokens["access_token"], "save_preset", namespace=namespace, randomizer="alttpr",
                        preset="mine", content="settings: {}")
    assert result["isError"] is False, result
    assert result["structuredContent"]["can_edit"] is True
    assert await models.Presets.filter(preset_name="mine").count() == 1


async def test_service_errors_reach_the_model_with_a_code(client):
    tokens = await connect(client, allow_changes=True)
    result = await call(client, tokens["access_token"], "get_preset_namespace", namespace="nobody")
    assert result["isError"] is True
    assert "not_found: There's no preset namespace called nobody." in result["content"][0]["text"]
    await presets.my_namespace(ALICE + 1, "bob")
    result = await call(client, tokens["access_token"], "delete_preset", namespace="bob", randomizer="alttpr",
                        preset="x")
    assert "forbidden: You can't change presets in this namespace." in result["content"][0]["text"]


async def test_unexpected_errors_are_opaque(client, monkeypatch, caplog):
    monkeypatch.setattr(presets, "list_namespaces", mock.AsyncMock(side_effect=RuntimeError("db exploded")))
    tokens = await connect(client)
    result = await call(client, tokens["access_token"], "list_preset_namespaces")
    assert result["content"][0]["text"].endswith("internal_error: The server hit an unexpected error.")
    assert "db exploded" not in result["content"][0]["text"]
    assert "Unhandled exception in MCP tool list_preset_namespaces" in caplog.text


async def test_roll_seed_on_a_read_only_connection(client, monkeypatch):
    generate = mock.AsyncMock(return_value=SimpleNamespace(url="https://alttpr.com/h/abc", hash="abc", code=["Bow"]))
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", generate)
    tokens = await connect(client)
    result = await call(client, tokens["access_token"], "roll_seed", randomizer="alttpr", preset="open", race=True)
    assert result["isError"] is False, result
    assert result["structuredContent"]["url"] == "https://alttpr.com/h/abc"
    assert generate.await_args.kwargs["tournament"] is True


# --- Personal access tokens on /api/v1 -------------------------------------------


def bearer(raw):
    return {"Authorization": f"Bearer {raw}"}


@pytest.fixture
def rest(db):
    return api.sahasrahbotapi.test_client()


async def test_token_signs_in_on_api_v1(rest):
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", True, None)
    resp = await rest.get("/api/v1/session", headers=bearer(raw))
    assert (await resp.get_json())["user"]["id"] == str(ALICE)


async def test_bad_token_is_401(rest):
    resp = await rest.get("/api/v1/session", headers=bearer("sb_pat_nope"))
    assert resp.status_code == 401
    assert "invalid, expired or revoked" in (await resp.get_json())["error"]


async def test_mcp_tokens_do_not_work_on_api_v1(rest, db):
    await mcp_auth.register_client("c", "Claude", [REDIRECT], ["authorization_code"], ["code"], mcp_auth.CLIENT_SCOPE)
    txn = mcp_auth.begin_authorization(mcp_auth.PendingAuthorization(
        client_id="c", redirect_uri=REDIRECT, redirect_uri_provided_explicitly=True, code_challenge="x", state=None,
        resource=None))
    code = parse_qs(urlsplit(await mcp_auth.approve(txn, ALICE, "alice", True)).query)["code"][0]
    access, _, _ = await mcp_auth.exchange_code(await mcp_auth.load_code("c", code))
    assert (await rest.get("/api/v1/session", headers=bearer(access))).status_code == 401


async def test_read_only_token_cannot_change_things(rest):
    namespace = await presets.my_namespace(ALICE, "alice")
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", True, None)
    resp = await rest.put(f"/api/v1/presets/namespaces/{namespace}/alttpr/mine", json={"content": "a: 1"},
                          headers=bearer(raw))
    assert resp.status_code == 403
    assert "read-only" in (await resp.get_json())["error"]


async def test_write_token_changes_things_without_the_csrf_header(rest):
    namespace = await presets.my_namespace(ALICE, "alice")
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", False, None)
    resp = await rest.put(f"/api/v1/presets/namespaces/{namespace}/alttpr/mine", json={"content": "a: 1"},
                          headers=bearer(raw))
    assert resp.status_code == 200, await resp.get_data()


async def test_read_only_token_can_roll_a_seed(rest, monkeypatch):
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", mock.AsyncMock(
        return_value=SimpleNamespace(url="https://alttpr.com/h/abc", hash="abc", code=None)))
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", True, None)
    resp = await rest.post("/api/v1/seeds", json={"randomizer": "alttpr", "preset": "open"}, headers=bearer(raw))
    assert resp.status_code == 201, await resp.get_data()
    assert (await resp.get_json())["hash"] == "abc"


async def test_seed_lookup(rest):
    await models.AuditGeneratedGames.create(randomizer="smz3", hash_id="xyz", permalink="https://samus.link/seed/xyz",
                                            settings={}, gentype="preset", genoption="normal")
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", True, None)
    resp = await rest.get("/api/v1/seeds/xyz", headers=bearer(raw))
    assert (await resp.get_json())["preset"] == "normal"
    assert (await rest.get("/api/v1/seeds/nope", headers=bearer(raw))).status_code == 404
    assert (await rest.get("/api/v1/seeds/xyz")).status_code == 401


@pytest.mark.parametrize("method, path, body", [
    ("GET", "/api/v1/tokens", None),
    ("POST", "/api/v1/tokens", {"name": "x"}),
    ("DELETE", "/api/v1/tokens/1", None),
    ("POST", "/api/v1/me/purge", None),
    ("GET", "/api/v1/oauth/requests/abc", None),
])
async def test_website_only_routes_refuse_tokens(rest, method, path, body):
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "script", False, None)
    resp = await rest.open(path, method=method, json=body, headers=bearer(raw))
    assert resp.status_code == 403
    assert "not with a token" in (await resp.get_json())["error"]

