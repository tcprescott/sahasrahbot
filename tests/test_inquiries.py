"""Inquiry buttons from the website: alttprbot/services/inquiries.py, the Discord
poster (alttprbot_discord/inquiries.py) and the /api/v1/servers/{id}/inquiries routes."""

from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import inquiries
from alttprbot.services.inquiries import Check
from alttprbot_discord import inquiries as discord_inquiries
from alttprbot_discord.cogs import inquiry as inquiry_cog
from tests.discord_fakes import FakeChannel, FakeGuild, FakeRole, permissions
from tests.test_api import CSRF, client, get_json, login, send_json  # noqa: F401 (fixtures)

GUILD = 5100
ADMIN = 51
MEMBER = 52


class FakePoster:
    def __init__(self):
        self.checks_result = [Check(True, "fine")]
        self.posted = []
        self.deleted = []
        self.located = []

    async def checks(self, guild_id, channel_id, role_id):
        return self.checks_result

    async def post(self, guild_id, channel_id, role_id):
        self.posted.append((guild_id, channel_id, role_id))
        return 9100 + len(self.posted)

    async def delete(self, channel_id, message_id):
        self.deleted.append((channel_id, message_id))

    async def locate(self, message_id, role_id):
        self.located.append(message_id)
        return (GUILD, 301) if message_id == 1 else None


@pytest.fixture
def poster(monkeypatch, directory):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], members={MEMBER: []},
                        channels=[(300, "#modmail"), (301, "#help")], roles=[(77, "@Mods")])
    fake = FakePoster()
    monkeypatch.setattr(inquiries, "_poster", fake)
    return fake


def test_a_poster_must_be_registered(monkeypatch):
    monkeypatch.setattr(inquiries, "_poster", None)
    with pytest.raises(RuntimeError):
        inquiries._get_poster()
    inquiries.register_poster(FakePoster())
    assert isinstance(inquiries._get_poster(), FakePoster)


async def test_post_list_and_remove(db, poster):
    await inquiries.register(1, 77)  # an old button: no server, so not listed
    posted = await inquiries.post(GUILD, ADMIN, 300, 77)
    assert poster.posted == [(GUILD, 300, 77)]
    assert posted["message_id"] == 9101
    assert posted["channel_name"] == "#modmail"
    assert posted["role_name"] == "@Mods"

    await models.InquiryMessageConfig.create(message_id=500, role_id=99, guild_id=GUILD, channel_id=999)
    listed = await inquiries.list_for_guild(GUILD, ADMIN)
    assert [i["message_id"] for i in listed] == [500, 9101]  # newest first
    assert listed[0]["channel_name"] is None  # gone channel and role
    assert listed[0]["role_name"] is None

    await inquiries.remove(GUILD, ADMIN, 9101)
    assert poster.deleted == [(300, 9101)]
    assert not await models.InquiryMessageConfig.exists(message_id=9101)
    with pytest.raises(NotFoundError):
        await inquiries.remove(GUILD, ADMIN, 1)  # not this server's

    actions = [e.action for e in await models.AuditLog.filter(guild_id=GUILD).order_by("id")]
    assert actions == ["inquiry.created", "inquiry.removed"]


async def test_remove_without_a_channel_just_forgets(db, poster):
    await models.InquiryMessageConfig.create(message_id=600, role_id=77, guild_id=GUILD)
    await inquiries.remove(GUILD, ADMIN, 600)
    assert poster.deleted == []
    assert not await models.InquiryMessageConfig.exists(message_id=600)


async def test_checks_must_pass_before_posting(db, poster):
    poster.checks_result = [Check(True, "fine"), Check(False, "Fix this first.")]
    assert await inquiries.check(GUILD, ADMIN, 300, 77) == poster.checks_result
    with pytest.raises(InvalidInputError, match="Fix this first."):
        await inquiries.post(GUILD, ADMIN, 300, 77)
    assert poster.posted == []


@pytest.mark.parametrize("channel, role, message", [(999, 77, "channel"), (300, 99, "role")])
async def test_channel_and_role_must_be_the_servers(db, poster, channel, role, message):
    with pytest.raises(InvalidInputError, match=message):
        await inquiries.check(GUILD, ADMIN, channel, role)


async def test_only_admins(db, poster):
    with pytest.raises(PermissionDeniedError):
        await inquiries.list_for_guild(GUILD, MEMBER)
    with pytest.raises(PermissionDeniedError):
        await inquiries.post(GUILD, MEMBER, 300, 77)
    with pytest.raises(PermissionDeniedError):
        await inquiries.remove(GUILD, MEMBER, 1)


async def test_older_messages_are_located_once(db, poster, monkeypatch):
    monkeypatch.setattr(inquiries, "_not_found", set())
    await inquiries.register(1, 77)
    await inquiries.register(2, 77)
    assert await inquiries.locate_older_messages() == 1
    assert [i["channel_name"] for i in await inquiries.list_for_guild(GUILD, ADMIN)] == ["#help"]
    # Message 2 isn't searched for again in this process; message 1 is done.
    assert await inquiries.locate_older_messages() == 0
    assert poster.located == [1, 2]
    actions = [e.action for e in await models.AuditLog.filter(guild_id=GUILD)]
    assert actions == ["inquiry.located"]

    # Pressing the button fills it in too, but never overwrites a known place.
    await inquiries.note_location(2, GUILD, 300)
    await inquiries.note_location(2, GUILD, 999)
    row = await models.InquiryMessageConfig.get(message_id=2)
    assert (row.guild_id, row.channel_id) == (GUILD, 300)


# --- the Discord side --------------------------------------------------------


def good_channel(guild, role):
    return FakeChannel(name="modmail", guild=guild, perms={
        guild.me.id: permissions(create_private_threads=True),
        guild.default_role.id: permissions(send_messages_in_threads=True),
        role.id: permissions(read_messages=True),
    })


def test_channel_checks():
    guild, role = FakeGuild(), FakeRole(500, name="Mods")
    channel = good_channel(guild, role)
    checks = discord_inquiries.channel_checks(channel, role, guild.me, guild.default_role)
    assert [c.text for c in checks] == [
        "SahasrahBot can create private threads in #modmail",
        "@Mods can see #modmail",
        "Members can't post in #modmail, only press the button",
        "Members can send messages in threads",
    ]
    assert all(c.ok for c in checks)

    channel.perms[guild.default_role.id] = permissions(send_messages=True)
    failing = [c.text for c in discord_inquiries.channel_checks(channel, role, guild.me, guild.default_role)
               if not c.ok]
    assert failing == ["@everyone can send messages in #modmail. Turn that off, or people will post there instead.",
                       "@everyone needs to be able to send messages in threads, or they can't write in their inquiry."]


def discord_bot(guild, channel, role):
    guild.get_channel = lambda cid: channel if cid == channel.id else None
    guild.get_role = lambda rid: role if rid == role.id else None
    return SimpleNamespace(get_guild=lambda gid: guild if gid == guild.id else None,
                           get_channel=lambda cid: channel if cid == channel.id else None,
                           fetch_channel=mock.AsyncMock())


async def test_discord_poster_checks_posts_and_deletes():
    guild, role = FakeGuild(), FakeRole(500, name="Mods")
    channel = good_channel(guild, role)
    channel.get_partial_message = lambda mid: SimpleNamespace(delete=mock.AsyncMock())
    poster = discord_inquiries.DiscordInquiryPoster(discord_bot(guild, channel, role))

    assert all(c.ok for c in await poster.checks(guild.id, channel.id, role.id))
    message_id = await poster.post(guild.id, channel.id, role.id)
    assert message_id == 800
    sent = channel.sent[0]
    assert "<@&500>" in sent.content
    assert isinstance(sent.view, inquiry_cog.ConfirmInquiryThread)
    await poster.delete(channel.id, message_id)
    with pytest.raises(InvalidInputError, match="isn't in this server"):
        await poster.checks(guild.id, 1, role.id)


@pytest.mark.parametrize("error, message", [
    (discord.Forbidden(SimpleNamespace(status=403, reason="x"), "no"), "isn't allowed to post"),
    (discord.HTTPException(SimpleNamespace(status=500, reason="x"), "boom"), "didn't accept"),
])
async def test_discord_poster_explains_refusals(error, message):
    guild, role = FakeGuild(), FakeRole(500)
    channel = good_channel(guild, role)
    channel.send = mock.AsyncMock(side_effect=error)
    poster = discord_inquiries.DiscordInquiryPoster(discord_bot(guild, channel, role))
    with pytest.raises(InvalidInputError, match=message):
        await poster.post(guild.id, channel.id, role.id)


async def test_discord_poster_delete_tolerates_a_gone_message_but_not_a_refusal():
    guild, role = FakeGuild(), FakeRole(500)
    channel = good_channel(guild, role)
    poster = discord_inquiries.DiscordInquiryPoster(discord_bot(guild, channel, role))
    gone = discord.NotFound(SimpleNamespace(status=404, reason="x"), "gone")
    channel.get_partial_message = lambda mid: SimpleNamespace(delete=mock.AsyncMock(side_effect=gone))
    await poster.delete(channel.id, 1)
    refused = discord.Forbidden(SimpleNamespace(status=403, reason="x"), "no")
    channel.get_partial_message = lambda mid: SimpleNamespace(delete=mock.AsyncMock(side_effect=refused))
    with pytest.raises(InvalidInputError, match="Delete it in Discord"):
        await poster.delete(channel.id, 1)


async def test_discord_poster_locates_an_older_message():
    role = FakeRole(500)
    readable = permissions(read_messages=True, read_message_history=True)
    guild = FakeGuild(guild_id=10, roles=[role])
    hidden = FakeChannel(channel_id=20, name="hidden", guild=guild)  # bot can't read it
    other = FakeChannel(channel_id=30, name="other", guild=guild, perms={guild.me.id: readable})
    other.fetch_message = mock.AsyncMock(side_effect=discord.NotFound(SimpleNamespace(status=404, reason="x"), "no"))
    broken = FakeChannel(channel_id=35, name="broken", guild=guild, perms={guild.me.id: readable})
    broken.fetch_message = mock.AsyncMock(
        side_effect=discord.HTTPException(SimpleNamespace(status=500, reason="x"), "boom"))
    home = FakeChannel(channel_id=40, name="home", guild=guild, perms={guild.me.id: readable})
    newer = FakeChannel(channel_id=9000, name="newer", guild=guild, perms={guild.me.id: readable})
    guild.text_channels = [hidden, other, broken, newer, home]
    bot = SimpleNamespace(guilds=[FakeGuild(guild_id=11), guild])
    poster = discord_inquiries.DiscordInquiryPoster(bot)

    assert await poster.locate(800, 500) == (10, 40)
    hidden.fetch_message.assert_not_awaited()
    newer.fetch_message.assert_not_awaited()  # made after the message
    assert await poster.locate(800, 999) is None  # role in no server
    home.fetch_message = other.fetch_message
    assert await poster.locate(800, 500) is None


def test_register_hands_the_service_a_poster(monkeypatch):
    monkeypatch.setattr(inquiries, "_poster", None)
    discord_inquiries.register(SimpleNamespace())
    assert isinstance(inquiries._get_poster(), discord_inquiries.DiscordInquiryPoster)


# --- the API -----------------------------------------------------------------


async def test_api(client, login, poster):
    login(ADMIN)
    status, body = await send_json(client, "POST", f"/api/v1/servers/{GUILD}/inquiries/check",
                                   {"channel_id": "300", "role_id": "77"})
    assert (status, body) == (200, {"checks": [{"ok": True, "text": "fine"}]})
    status, body = await send_json(client, "POST", f"/api/v1/servers/{GUILD}/inquiries",
                                   {"channel_id": "300", "role_id": "77"})
    assert status == 201
    assert body["message_id"] == "9101"
    assert body["jump_url"] == f"https://discord.com/channels/{GUILD}/300/9101"
    status, body = await get_json(client, f"/api/v1/servers/{GUILD}/inquiries")
    assert [i["channel_name"] for i in body["inquiries"]] == ["#modmail"]
    status, body = await send_json(client, "POST", f"/api/v1/servers/{GUILD}/inquiries",
                                   {"channel_id": "x", "role_id": "77"})
    assert status == 400
    resp = await client.delete(f"/api/v1/servers/{GUILD}/inquiries/9101", headers=CSRF)
    assert resp.status_code == 204

    login(MEMBER)
    assert (await get_json(client, f"/api/v1/servers/{GUILD}/inquiries"))[0] == 403
