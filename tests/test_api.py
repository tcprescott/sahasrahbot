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
from alttprbot.services import bots


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


async def make_key(key="secret", type_="racetimecmd", subtype=None):
    auth_key = await models.AuthorizationKeys.create(key=key, name="test")
    await models.AuthorizationKeyPermissions.create(auth_key=auth_key, type=type_, subtype=subtype)


async def test_racetime_cmd_requires_key_for_category(client):
    await make_key(key="k", type_="racetimecmd", subtype="alttpr")
    payload = {"category": "smz3", "room": "r", "cmd": "!race open"}
    resp = await client.post("/api/racetime/cmd?auth_key=k", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 403
