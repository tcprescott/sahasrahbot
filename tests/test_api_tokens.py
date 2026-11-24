"""Tests for the services behind the REST API's tokens and the MCP server's OAuth:
``alttprbot/services/api_tokens.py``, ``mcp_auth.py`` and ``seeds.py``."""

from datetime import timedelta
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import accounts, api_tokens, mcp_auth, seeds

ALICE = 91000000000000001
BOB = 91000000000000002


@pytest.fixture(autouse=True)
def _no_pending(monkeypatch):
    monkeypatch.setattr(mcp_auth, "_pending", {})


# --- Personal access tokens ---------------------------------------------------


async def test_create_personal_token_stores_only_a_hash(db):
    raw, row = await api_tokens.create_personal_token(ALICE, "alice", "  My script ", True, 90)
    assert raw.startswith("sb_pat_")
    assert row["name"] == "My script"
    assert row["kind"] == "token"
    assert row["read_only"] is True
    assert row["prefix"] == raw[:11]
    assert row["expires_at"] - row["created_at"] > timedelta(days=89)
    stored = await models.ApiToken.get(id=row["id"])
    assert stored.token_hash == api_tokens.hash_token(raw)
    assert raw not in (stored.token_hash, stored.token_prefix)


async def test_create_personal_token_that_never_expires(db):
    _, row = await api_tokens.create_personal_token(ALICE, "alice", "forever", False, None)
    assert row["expires_at"] is None
    assert row["read_only"] is False


@pytest.mark.parametrize(
    "name, days, message",
    [("", 30, "Give the token a name"), ("x" * 101, 30, "at most 100"), ("ok", 7, "30, 90 or 365")],
)
async def test_create_personal_token_refuses_bad_input(db, name, days, message):
    with pytest.raises(InvalidInputError, match=message):
        await api_tokens.create_personal_token(ALICE, "alice", name, True, days)


async def test_create_personal_token_caps_how_many(db, monkeypatch):
    monkeypatch.setattr(api_tokens, "MAX_TOKENS_PER_USER", 2)
    await api_tokens.create_personal_token(ALICE, "alice", "a", True, None)
    await api_tokens.create_personal_token(ALICE, "alice", "b", True, None)
    with pytest.raises(InvalidInputError, match="at most 2 tokens"):
        await api_tokens.create_personal_token(ALICE, "alice", "c", True, None)


async def test_authenticate_checks_origin_expiry_and_revocation(db):
    raw, row = await api_tokens.create_personal_token(ALICE, "alice", "a", True, 30)
    token = await api_tokens.authenticate(raw, api_tokens.PAT)
    assert token.discord_user_id == ALICE
    assert token.last_used_at is not None
    assert await api_tokens.authenticate(raw, api_tokens.OAUTH) is None
    assert await api_tokens.authenticate("sb_pat_wrong", api_tokens.PAT) is None
    assert await api_tokens.authenticate("", api_tokens.PAT) is None

    await models.ApiToken.filter(id=row["id"]).update(expires_at=api_tokens.now() - timedelta(seconds=1))
    assert await api_tokens.authenticate(raw, api_tokens.PAT) is None


async def test_authenticate_marks_use_at_most_once_a_minute(db):
    raw, row = await api_tokens.create_personal_token(ALICE, "alice", "a", True, None)
    first = (await api_tokens.authenticate(raw, api_tokens.PAT)).last_used_at
    second = (await api_tokens.authenticate(raw, api_tokens.PAT)).last_used_at
    assert second == first


async def test_list_and_revoke_are_per_user(db):
    _, mine = await api_tokens.create_personal_token(ALICE, "alice", "mine", True, None)
    _, theirs = await api_tokens.create_personal_token(BOB, "bob", "theirs", True, None)
    assert [t["name"] for t in await api_tokens.list_for_user(ALICE)] == ["mine"]

    with pytest.raises(NotFoundError):
        await api_tokens.revoke(theirs["id"], ALICE)
    await api_tokens.revoke(mine["id"], ALICE)
    assert await api_tokens.list_for_user(ALICE) == []
    with pytest.raises(NotFoundError, match="already revoked"):
        await api_tokens.revoke(mine["id"], ALICE)
    assert len(await api_tokens.list_for_user(BOB)) == 1


async def test_list_hides_expired_tokens(db):
    _, row = await api_tokens.create_personal_token(ALICE, "alice", "old", True, 30)
    await models.ApiToken.filter(id=row["id"]).update(expires_at=api_tokens.now() - timedelta(days=1))
    assert await api_tokens.list_for_user(ALICE) == []


async def test_purge_deletes_tokens_and_codes(db):
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "a", True, None)
    await accounts.purge(ALICE)
    assert await models.ApiToken.filter(discord_user_id=ALICE).count() == 0
    assert await api_tokens.authenticate(raw, api_tokens.PAT) is None


# --- MCP OAuth ----------------------------------------------------------------

REDIRECT = "https://claude.ai/api/mcp/auth_callback"


@pytest.mark.parametrize(
    "uri, allowed",
    [
        (REDIRECT, True),
        ("http://localhost:3334/callback", True),
        ("http://127.0.0.1/cb", True),
        ("http://evil.example/cb", False),
        ("javascript:alert(1)", False),
        ("cursor://anysphere.cursor-mcp/oauth/callback", True),
        ("https://claude.ai/cb#frag", False),
        ("not a uri", False),
    ],
)
def test_redirect_uri_rules(uri, allowed):
    assert mcp_auth.is_allowed_redirect_uri(uri) is allowed


def test_redirect_target_names_the_host():
    assert mcp_auth.redirect_target(REDIRECT) == "claude.ai"
    assert mcp_auth.scope_for(True) == mcp_auth.READ_SCOPE
    assert mcp_auth.scope_for(False) == mcp_auth.CLIENT_SCOPE


async def _client(client_id="client-1"):
    await mcp_auth.register_client(client_id, "Claude", [REDIRECT], ["authorization_code", "refresh_token"],
                                   ["code"], mcp_auth.CLIENT_SCOPE)
    return await mcp_auth.get_client(client_id)


def _pending(client, **overrides):
    values = dict(client_id=client.client_id, client_name=client.client_name, redirect_uri=REDIRECT,
                  redirect_uri_provided_explicitly=True, code_challenge="challenge", state="xyz",
                  scope=mcp_auth.CLIENT_SCOPE, resource=None)
    values.update(overrides)
    return mcp_auth.PendingAuthorization(**{k: v for k, v in values.items()
                                            if k in mcp_auth.PendingAuthorization.__dataclass_fields__})


async def _approve(client, allow_changes=False):
    txn = mcp_auth.begin_authorization(_pending(client))
    redirect = await mcp_auth.approve(txn, ALICE, "alice", allow_changes)
    query = parse_qs(urlsplit(redirect).query)
    return redirect, query


async def test_describe_request_and_expiry(db):
    client = await _client()
    txn = mcp_auth.begin_authorization(_pending(client))
    assert await mcp_auth.describe_request(txn) == {"client_name": "Claude", "redirect_target": "claude.ai"}
    with pytest.raises(NotFoundError):
        await mcp_auth.describe_request("nope")

    mcp_auth._pending[txn].created_at -= mcp_auth.PENDING_TTL + timedelta(seconds=1)
    with pytest.raises(NotFoundError):
        await mcp_auth.describe_request(txn)


async def test_approve_returns_a_single_use_code(db):
    client = await _client()
    redirect, query = await _approve(client)
    assert redirect.startswith(REDIRECT + "?")
    assert query["state"] == ["xyz"]
    raw_code = query["code"][0]
    code = await mcp_auth.load_code(client.client_id, raw_code)
    assert code.read_only is True
    assert await mcp_auth.load_code("other-client", raw_code) is None

    access, refresh, expires_in = await mcp_auth.exchange_code(code)
    assert access.startswith("sb_mcp_")
    assert refresh.startswith("sb_mcpr_")
    assert expires_in == int(mcp_auth.ACCESS_TOKEN_TTL.total_seconds())
    token = await api_tokens.authenticate(access, api_tokens.OAUTH)
    assert (token.discord_user_id, token.read_only, token.name) == (ALICE, True, "Claude")

    assert await mcp_auth.load_code(client.client_id, raw_code) is None
    with pytest.raises(Exception):
        await mcp_auth.exchange_code(code)


async def test_an_approved_request_cannot_be_answered_twice(db):
    client = await _client()
    txn = mcp_auth.begin_authorization(_pending(client))
    await mcp_auth.approve(txn, ALICE, "alice", True)
    with pytest.raises(NotFoundError):
        await mcp_auth.approve(txn, ALICE, "alice", True)


async def test_allow_changes_grants_write(db):
    client = await _client()
    _, query = await _approve(client, allow_changes=True)
    code = await mcp_auth.load_code(client.client_id, query["code"][0])
    access, _, _ = await mcp_auth.exchange_code(code)
    assert (await api_tokens.authenticate(access, api_tokens.OAUTH)).read_only is False


async def test_deny_sends_access_denied(db):
    client = await _client()
    txn = mcp_auth.begin_authorization(_pending(client))
    query = parse_qs(urlsplit(mcp_auth.deny(txn)).query)
    assert query == {"error": ["access_denied"], "state": ["xyz"]}
    with pytest.raises(NotFoundError):
        mcp_auth.deny(txn)


async def test_refresh_rotates_both_tokens_once(db):
    client = await _client()
    _, query = await _approve(client)
    access, refresh, _ = await mcp_auth.exchange_code(await mcp_auth.load_code(client.client_id, query["code"][0]))

    record = await mcp_auth.load_refresh_token(client.client_id, refresh)
    assert record is not None
    assert await mcp_auth.load_refresh_token("other-client", refresh) is None
    new_access, new_refresh, _ = await mcp_auth.exchange_refresh(record)
    assert new_access != access
    assert new_refresh != refresh
    assert await api_tokens.authenticate(access, api_tokens.OAUTH) is None
    assert await api_tokens.authenticate(new_access, api_tokens.OAUTH) is not None
    assert await mcp_auth.load_refresh_token(client.client_id, refresh) is None
    # The client shows once on the API access page, under the client's name.
    assert [(t["name"], t["kind"]) for t in await api_tokens.list_for_user(ALICE)] == [("Claude", "client")]


async def test_revoke_disconnects_the_client(db):
    client = await _client()
    _, query = await _approve(client)
    access, refresh, _ = await mcp_auth.exchange_code(await mcp_auth.load_code(client.client_id, query["code"][0]))
    await mcp_auth.revoke(await mcp_auth.load_access_token(access))
    assert await mcp_auth.load_access_token(access) is None
    assert await mcp_auth.load_refresh_token(client.client_id, refresh) is None


async def test_pending_requests_are_capped(db, monkeypatch):
    monkeypatch.setattr(mcp_auth, "MAX_PENDING", 3)
    client = await _client()
    txns = [mcp_auth.begin_authorization(_pending(client)) for _ in range(5)]
    assert len(mcp_auth._pending) <= 3
    assert txns[-1] in mcp_auth._pending


# --- Seeds ------------------------------------------------------------------------


def _seed(**fields):
    return SimpleNamespace(url="https://alttpr.com/h/abc", hash="abc", code=["Bow", "Bomb"], **fields)


async def test_roll_alttpr(monkeypatch):
    generate = mock.AsyncMock(return_value=_seed())
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", generate)
    rolled = await seeds.roll("alttpr", "open", seeds.RollOptions(race=True, branch="beeta"))
    assert rolled == {"randomizer": "alttpr", "preset": "open", "url": "https://alttpr.com/h/abc", "hash": "abc",
                      "file_select_code": ["Bow", "Bomb"], "spoiler_url": None, "custom_instructions": None}
    assert generate.await_args.kwargs == {"hints": False, "spoilers": "off", "tournament": True,
                                          "allow_quickswap": True, "branch": "beeta"}


async def test_roll_alttpr_that_fails(monkeypatch):
    monkeypatch.setattr(generator.ALTTPRPreset, "generate", mock.AsyncMock(return_value=None))
    with pytest.raises(InvalidInputError, match="could not generate"):
        await seeds.roll("alttpr", "open")


async def test_roll_mystery(monkeypatch):
    mystery = SimpleNamespace(seed=_seed(), custom_instructions="Swords are random")
    monkeypatch.setattr(generator.ALTTPRMystery, "generate", mock.AsyncMock(return_value=mystery))
    rolled = await seeds.roll("alttprmystery", "weighted")
    assert rolled["custom_instructions"] == "Swords are random"


async def test_roll_smz3_with_spoiler(monkeypatch):
    async def generate(self, **kwargs):
        self.seed = SimpleNamespace(url="https://samus.link/seed/x", slug_id="x")

    monkeypatch.setattr(generator.SMZ3Preset, "generate", generate)
    monkeypatch.setattr(generator.SMZ3Preset, "spoiler_url", lambda self: "https://samus.link/spoiler/x")
    rolled = await seeds.roll("smz3", "normal", seeds.RollOptions(spoiler_race=True))
    assert (rolled["hash"], rolled["spoiler_url"], rolled["file_select_code"]) == ("x", "https://samus.link/spoiler/x", None)


async def test_roll_sm(monkeypatch):
    async def generate(self, **kwargs):
        self.seed = SimpleNamespace(url="https://sm.samus.link/seed/y", slug_id="y")

    monkeypatch.setattr(generator.SMPreset, "generate", generate)
    rolled = await seeds.roll("sm", "rls")
    assert (rolled["url"], rolled["spoiler_url"]) == ("https://sm.samus.link/seed/y", None)


async def test_roll_a_missing_preset(monkeypatch):
    monkeypatch.setattr(generator.ALTTPRPreset, "generate",
                        mock.AsyncMock(side_effect=generator.PresetNotFoundException("nope")))
    with pytest.raises(NotFoundError, match="no alttpr preset called nope"):
        await seeds.roll("alttpr", "nope")


@pytest.mark.parametrize(
    "randomizer, preset, options, message",
    [("ootr", "x", seeds.RollOptions(), "not ootr"), ("alttpr", "x", seeds.RollOptions(branch="dev"), "branch"),
     ("alttpr", "", seeds.RollOptions(), "Name the preset")],
)
async def test_roll_refuses_bad_input(randomizer, preset, options, message):
    with pytest.raises(InvalidInputError, match=message):
        await seeds.roll(randomizer, preset, options)


async def test_lookup(db):
    await models.AuditGeneratedGames.create(randomizer="alttpr", hash_id="abc", permalink="https://alttpr.com/h/abc",
                                            settings={"secret": True}, gentype="preset", genoption="open")
    found = await seeds.lookup("abc")
    assert {k: found[k] for k in ("hash", "randomizer", "kind", "preset", "url")} == {
        "hash": "abc", "randomizer": "alttpr", "kind": "preset", "preset": "open", "url": "https://alttpr.com/h/abc"}
    assert "settings" not in found
    with pytest.raises(NotFoundError):
        await seeds.lookup("zzz")
