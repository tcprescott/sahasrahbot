"""The server directory as the website edits it: alttprbot/services/discord_servers.py
(the website functions), alttprbot_discord/server_directory.py (checking invites and
posting) and the /api/v1/servers/<id>/directory routes. The /discordservers commands
are in tests/test_cogs_community.py and the older service functions in
tests/test_discord_services.py."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import audit, discord_servers
from alttprbot_discord import server_directory
from tests.discord_fakes import FakeChannel, FakeGuild
from tests.test_api import CSRF, client, get_json, login, send_json  # noqa: F401  (fixtures)

GUILD, OTHER_GUILD, ADMIN, OUTSIDER = 5, 6, 7, 11


@pytest.fixture
def discord_side(monkeypatch):
    """Registers a fake Discord for the directory: invites starting "bad" don't work, and
    posted layouts are kept in ``posted``."""
    posted = []

    async def lookup(code):
        if code.startswith("bad"):
            raise InvalidInputError("That invite doesn't work.")
        return discord_servers.InviteInfo(code=code, server_name=f"Server {code}", member_count=42)

    async def poster(guild_id, layout):
        posted.append((guild_id, layout))

    monkeypatch.setattr(discord_servers, "_lookup_invite", None)
    monkeypatch.setattr(discord_servers, "_poster", None)
    discord_servers.register(lookup, poster)
    return SimpleNamespace(posted=posted)


@pytest.mark.parametrize("text, code", [
    ("abc123", "abc123"),
    ("https://discord.gg/abc123", "abc123"),
    ("discord.gg/abc-123/", "abc-123"),
    ("https://discord.com/invite/AbC?event=1", "AbC"),
    ("  https://www.discordapp.com/invite/xyz  ", "xyz"),
])
def test_invite_code(text, code):
    assert discord_servers.invite_code(text) == code


@pytest.mark.parametrize("text", ["", "https://example.com/x y", "a" * 46, "https://discord.gg/"])
def test_bad_invite_codes(text):
    with pytest.raises(InvalidInputError):
        discord_servers.invite_code(text)


async def test_nothing_registered_is_a_clear_error(db, monkeypatch):
    monkeypatch.setattr(discord_servers, "_lookup_invite", None)
    with pytest.raises(RuntimeError, match="gateways.register"):
        await discord_servers.lookup_invite("abc")


async def test_directory_order_edits_and_unposted_changes(db, discord_side):
    await discord_servers.create_category(GUILD, 100, " Randomizers ", "Main hubs")
    await discord_servers.create_category(GUILD, 101, "Speedrunning", "  ")
    await discord_servers.create_category(OTHER_GUILD, 300, "Elsewhere", None)
    randos, speed = await discord_servers.list_categories(GUILD)
    assert (randos.category_title, randos.order, speed.order, speed.category_description) == ("Randomizers", 0, 1, None)

    await discord_servers.add_server_from_invite(GUILD, randos.id, "https://discord.gg/alttpr", "ALTTPR")
    await discord_servers.add_server_from_invite(GUILD, randos.id, "smz3", "SMZ3")
    with pytest.raises(InvalidInputError):
        await discord_servers.add_server_from_invite(GUILD, randos.id, "bad1", "Broken")
    with pytest.raises(InvalidInputError, match="text shown"):
        await discord_servers.add_server_from_invite(GUILD, randos.id, "ok", " ")

    directory = await discord_servers.get_directory(GUILD)
    assert [(e.category.category_title, [s.invite_id for s in e.servers]) for e in directory.categories] == [
        ("Randomizers", ["alttpr", "smz3"]), ("Speedrunning", [])]
    assert (directory.last_posted_at, directory.unposted_changes) == (None, True)

    alttpr, smz3 = directory.categories[0].servers
    await discord_servers.reorder_servers(GUILD, randos.id, [smz3.id, alttpr.id])
    await discord_servers.reorder_categories(GUILD, [speed.id, randos.id])
    directory = await discord_servers.get_directory(GUILD)
    assert [e.category.category_title for e in directory.categories] == ["Speedrunning", "Randomizers"]
    assert [s.invite_id for s in directory.categories[1].servers] == ["smz3", "alttpr"]

    layout = await discord_servers.post(GUILD)
    assert discord_side.posted == [(GUILD, layout)]
    assert layout.channel_ids == [101, 100]
    assert [discord_servers.page_text(p) for p in layout.pages] == [
        "**__Randomizers__**\nSMZ3: https://discord.gg/smz3\nALTTPR: https://discord.gg/alttpr"]
    directory = await discord_servers.get_directory(GUILD)
    assert directory.last_posted_at is not None and directory.unposted_changes is False

    # Moving a server: it goes last in the other category, and only a new invite is checked.
    await discord_servers.edit_server(GUILD, alttpr.id, speed.id, "discord.gg/alttpr", "ALTTPR main")
    with pytest.raises(InvalidInputError):
        await discord_servers.edit_server(GUILD, alttpr.id, speed.id, "bad2", "ALTTPR main")
    await discord_servers.edit_category(GUILD, randos.id, 102, "Rando", None)
    directory = await discord_servers.get_directory(GUILD)
    assert [(e.category.category_title, e.category.channel_id, [s.server_description for s in e.servers])
            for e in directory.categories] == [("Speedrunning", 101, ["ALTTPR main"]), ("Rando", 102, ["SMZ3"])]
    assert directory.unposted_changes is True

    await discord_servers.remove_category(GUILD, randos.id)
    assert not await models.DiscordServerLists.filter(id=smz3.id).exists()  # its servers go with it

    actions = [e.action for e in await models.AuditLog.filter(guild_id=GUILD).order_by('id')]
    assert actions.count(audit.SERVER_LIST_REORDERED) == 2
    assert audit.SERVER_LIST_POSTED in actions
    assert all(audit.area_of(a) == 'server' for a in actions)


async def test_reorder_must_list_everything_once(db, discord_side):
    await discord_servers.create_category(GUILD, 100, "A", None)
    await discord_servers.create_category(GUILD, 100, "B", None)
    a, b = await discord_servers.list_categories(GUILD)
    for ids in ([a.id], [a.id, a.id], [a.id, b.id, 999]):
        with pytest.raises(InvalidInputError):
            await discord_servers.reorder_categories(GUILD, ids)
    with pytest.raises(NotFoundError):
        await discord_servers.reorder_servers(OTHER_GUILD, a.id, [])


async def test_posting_an_empty_directory_is_refused(db, discord_side):
    with pytest.raises(InvalidInputError, match="Add a category"):
        await discord_servers.post(GUILD)
    assert discord_side.posted == []


async def test_long_text_is_refused(db, discord_side):
    with pytest.raises(InvalidInputError, match="at most 200"):
        await discord_servers.create_category(GUILD, 100, "x" * 201, None)
    with pytest.raises(InvalidInputError, match="Give the title"):
        await discord_servers.create_category(GUILD, 100, "", None)


# --- Discord ----------------------------------------------------------------------


def _http_error(cls, status):
    return cls(SimpleNamespace(status=status, reason="nope"), "nope")


async def test_lookup_invite_asks_discord():
    bot = SimpleNamespace(fetch_invite=mock.AsyncMock(return_value=SimpleNamespace(
        code="abc", guild=SimpleNamespace(name="ALTTPR"), approximate_member_count=10,
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc))))
    info = await server_directory.lookup_invite(bot, "abc")
    assert (info.code, info.server_name, info.member_count) == ("abc", "ALTTPR", 10)
    bot.fetch_invite.assert_awaited_with("abc", with_counts=True, with_expiration=True)


@pytest.mark.parametrize("result, message", [
    (_http_error(discord.NotFound, 404), "doesn't work"),
    (_http_error(discord.HTTPException, 500), "couldn't check"),
    (SimpleNamespace(code="abc", guild=None), "isn't for a server"),
])
async def test_lookup_invite_failures(result, message):
    fetch = mock.AsyncMock(side_effect=result) if isinstance(result, Exception) else mock.AsyncMock(return_value=result)
    with pytest.raises(InvalidInputError, match=message):
        await server_directory.lookup_invite(SimpleNamespace(fetch_invite=fetch), "abc")


async def test_post_layout_reports_missing_channels_and_permissions(db):
    category = await discord_servers.add_category(1, 100, "Randomizers")
    await discord_servers.add_server(1, category.id, "abc", "ALTTPR")
    layout = await discord_servers.server_list_layout(1)

    with pytest.raises(InvalidInputError, match="can't see the channel <#100>"):
        await server_directory.post_layout(FakeGuild(guild_id=1, channels=[]), "bot", layout)

    channel = FakeChannel(channel_id=100, name="servers")
    channel.purge.side_effect = _http_error(discord.Forbidden, 403)
    with pytest.raises(InvalidInputError, match="Manage Messages in #servers"):
        await server_directory.post_layout(FakeGuild(guild_id=1, channels=[channel]), "bot", layout)


async def test_register_posts_through_the_bot(db, monkeypatch):
    monkeypatch.setattr(discord_servers, "_lookup_invite", None)
    monkeypatch.setattr(discord_servers, "_poster", None)
    guild = FakeGuild(guild_id=1, channels=[FakeChannel(channel_id=100, name="servers")])
    bot = SimpleNamespace(user="bot", get_guild=lambda gid: guild if gid == 1 else None,
                          fetch_invite=mock.AsyncMock(return_value=SimpleNamespace(code="abc", guild=SimpleNamespace(name="A"))))
    server_directory.register(bot)
    category = await discord_servers.add_category(1, 100, "Randomizers")
    await discord_servers.add_server(1, category.id, "abc", "ALTTPR")
    await discord_servers.add_category(2, 200, "Gone")

    await discord_servers.post(1)
    assert [m.content for m in guild.get_channel(100).sent] == ["**__Randomizers__**\nALTTPR: https://discord.gg/abc"]
    assert (await discord_servers.lookup_invite("https://discord.gg/abc")).server_name == "A"
    with pytest.raises(InvalidInputError, match="isn't in that server"):
        await discord_servers.post(2)


# --- /api/v1 ------------------------------------------------------------------------

BASE = f"/api/v1/servers/{GUILD}/directory"


async def test_api_edits_the_directory(client, login, directory, discord_side):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], channels=[(100, "#partners")])
    login(ADMIN)

    assert await get_json(client, BASE) == (200, {"guild_id": str(GUILD), "categories": [], "last_posted_at": None,
                                                  "unposted_changes": False, "servers_per_message": 10})
    status, body = await send_json(client, "POST", f"{BASE}/categories",
                                   {"title": "Randomizers", "description": "Hubs", "channel_id": "100"})
    assert status == 201
    [cat] = body["categories"]
    assert (cat["title"], cat["description"], cat["channel_id"]) == ("Randomizers", "Hubs", "100")
    assert (await send_json(client, "POST", f"{BASE}/categories", {"title": "X", "channel_id": ""}))[0] == 400

    status, body = await send_json(client, "POST", f"{BASE}/categories/{cat['id']}/servers",
                                   {"invite": "https://discord.gg/alttpr", "description": "ALTTPR"})
    assert (status, body["categories"][0]["servers"][0]["invite_code"]) == (201, "alttpr")
    status, body = await send_json(client, "POST", f"{BASE}/categories/{cat['id']}/servers",
                                   {"invite": "bad", "description": "Broken"})
    assert (status, body) == (400, {"error": "That invite doesn't work."})

    status, body = await send_json(client, "POST", f"{BASE}/categories/{cat['id']}/servers",
                                   {"invite": "smz3", "description": "SMZ3"})
    a, b = body["categories"][0]["servers"]
    status, body = await send_json(client, "PUT", f"{BASE}/categories/{cat['id']}/order", {"ids": [b["id"], a["id"]]})
    assert [s["invite_code"] for s in body["categories"][0]["servers"]] == ["smz3", "alttpr"]

    status, body = await send_json(client, "PUT", f"{BASE}/servers/{a['id']}",
                                   {"invite": "alttpr", "description": "ALTTPR main", "category_id": cat["id"]})
    assert body["categories"][0]["servers"][1]["description"] == "ALTTPR main"

    status, body = await send_json(client, "PUT", f"{BASE}/categories/{cat['id']}",
                                   {"title": "Rando", "description": None, "channel_id": "100"})
    assert (body["categories"][0]["title"], body["categories"][0]["description"]) == ("Rando", None)
    assert (await send_json(client, "PUT", f"{BASE}/order", {"ids": [cat["id"]]}))[0] == 200

    status, body = await get_json(client, f"{BASE}/invite?invite=discord.gg/zelda")
    assert (status, body["code"], body["server_name"], body["member_count"]) == (200, "zelda", "Server zelda", 42)

    assert (await get_json(client, BASE))[1]["unposted_changes"] is True
    status, body = await send_json(client, "POST", f"{BASE}/post", {})
    assert (status, body) == (200, {"messages": 1, "channel_ids": ["100"]})
    body = (await get_json(client, BASE))[1]
    assert body["unposted_changes"] is False and body["last_posted_at"]

    assert (await send_json(client, "DELETE", f"{BASE}/servers/{b['id']}"))[0] == 200
    status, body = await send_json(client, "DELETE", f"{BASE}/categories/{cat['id']}")
    assert (status, body["categories"]) == (200, [])


async def test_api_is_for_the_servers_admins(client, login, directory, discord_side):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN])
    directory.add_guild(OTHER_GUILD, name="Other", admins=[OUTSIDER])
    other = await discord_servers.add_category(OTHER_GUILD, 300, "Theirs")

    login(OUTSIDER)
    assert (await get_json(client, BASE))[0] == 403
    assert (await send_json(client, "POST", f"{BASE}/post", {}))[0] == 403
    login(None)
    assert (await get_json(client, BASE))[0] == 401

    login(ADMIN)  # another server's category, through this server's URL
    assert (await send_json(client, "DELETE", f"{BASE}/categories/{other.id}"))[0] == 404
    assert (await send_json(client, "PUT", f"{BASE}/categories/{other.id}",
                            {"title": "Mine", "channel_id": "1"}))[0] == 404
    assert (await models.DiscordServerCategories.get(id=other.id)).category_title == "Theirs"
