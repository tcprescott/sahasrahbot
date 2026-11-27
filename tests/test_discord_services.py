"""Tests for the services behind the Discord cogs: multiworld (/smmulti), the Discord
server list (/discordservers), reaction roles ($rr/$rg) and voice roles.

They pin what the cogs did before their data access moved into ``alttprbot/services/``.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError, SahasrahBotException
from alttprbot.services import discord_servers, multiworld, voice_roles

OWNER = 111
OTHER = 222
MSG = 9000

# ---------------------------------------------------------------------------
# multiworld
# ---------------------------------------------------------------------------


async def test_multiworld_create_is_open(db):
    mw = await multiworld.create(MSG, OWNER)
    assert (mw.owner_id, mw.status, mw.randomizer, mw.preset) == (OWNER, "STARTED", None, None)


async def test_multiworld_owner_only_actions(db):
    await multiworld.create(MSG, OWNER)
    with pytest.raises(multiworld.MultiworldNotAuthorized):
        await multiworld.set_randomizer(MSG, OTHER, "smz3")
    with pytest.raises(multiworld.MultiworldNotAuthorized):
        await multiworld.set_preset(MSG, OTHER, "normal")
    with pytest.raises(multiworld.MultiworldNotAuthorized):
        await multiworld.check_can_start(MSG, OTHER)
    with pytest.raises(multiworld.MultiworldNotAuthorized):
        await multiworld.cancel(MSG, OTHER)
    mw = await multiworld.get(MSG)
    assert (mw.randomizer, mw.preset, mw.status) == (None, None, "STARTED")


async def test_multiworld_changing_randomizer_clears_preset(db):
    await multiworld.create(MSG, OWNER)
    await multiworld.set_randomizer(MSG, OWNER, "smz3")
    await multiworld.set_preset(MSG, OWNER, "normal")
    assert (await multiworld.get(MSG)).preset == "normal"

    mw = await multiworld.set_randomizer(MSG, OWNER, "sm")
    assert (mw.randomizer, mw.preset) == ("sm", None)
    assert (await multiworld.get(MSG)).preset is None


async def test_multiworld_start_needs_randomizer_and_preset(db):
    await multiworld.create(MSG, OWNER)
    with pytest.raises(multiworld.MultiworldNotReady):
        await multiworld.check_can_start(MSG, OWNER)
    await multiworld.set_randomizer(MSG, OWNER, "smz3")
    with pytest.raises(multiworld.MultiworldNotReady):
        await multiworld.check_can_start(MSG, OWNER)
    await multiworld.set_preset(MSG, OWNER, "normal")
    assert (await multiworld.check_can_start(MSG, OWNER)).preset == "normal"


async def test_multiworld_join_and_leave(db):
    await multiworld.create(MSG, OWNER)
    assert await multiworld.join(MSG, OWNER) is True
    assert await multiworld.join(MSG, OTHER) is True
    assert await multiworld.join(MSG, OWNER) is False  # already signed up
    assert await multiworld.entrant_ids(MSG) == [OWNER, OTHER]

    await multiworld.leave(MSG, OWNER)
    await multiworld.leave(MSG, OWNER)  # leaving twice is fine
    assert await multiworld.entrant_ids(MSG) == [OTHER]


async def test_multiworld_entrants_are_per_game(db):
    await multiworld.create(MSG, OWNER)
    await multiworld.create(MSG + 1, OWNER)
    await multiworld.join(MSG, OTHER)
    assert await multiworld.entrant_ids(MSG + 1) == []


def test_multiworld_needs_two_players():
    assert not multiworld.has_enough_players(1)
    assert multiworld.has_enough_players(2)


async def test_multiworld_start_rolls_seed_and_closes(db, monkeypatch):
    await multiworld.create(MSG, OWNER)
    await multiworld.set_randomizer(MSG, OWNER, "smz3")
    await multiworld.set_preset(MSG, OWNER, "normal")
    mw = await multiworld.check_can_start(MSG, OWNER)

    seed = SimpleNamespace(url="https://samus.link/multiworld/abc")
    generate = mock.AsyncMock(return_value=seed)
    monkeypatch.setattr(multiworld, "generate_multiworld", generate)

    assert await multiworld.start(mw, ["Alice", "Bob"]) is seed
    generate.assert_awaited_once_with("normal", ["Alice", "Bob"], tournament=False, randomizer="smz3")
    assert (await multiworld.get(MSG)).status == "CLOSED"


async def test_multiworld_failed_roll_leaves_game_open(db, monkeypatch):
    await multiworld.create(MSG, OWNER)
    await multiworld.set_randomizer(MSG, OWNER, "sm")
    await multiworld.set_preset(MSG, OWNER, "casual_full")
    mw = await multiworld.check_can_start(MSG, OWNER)
    monkeypatch.setattr(multiworld, "generate_multiworld", mock.AsyncMock(side_effect=RuntimeError("down")))

    with pytest.raises(RuntimeError):
        await multiworld.start(mw, ["Alice", "Bob"])
    assert (await multiworld.get(MSG)).status == "STARTED"


async def test_multiworld_cancel(db):
    await multiworld.create(MSG, OWNER)
    await multiworld.cancel(MSG, OWNER)
    assert (await multiworld.get(MSG)).status == "CANCELLED"


# ---------------------------------------------------------------------------
# discord_servers
# ---------------------------------------------------------------------------


async def test_discord_server_categories(db):
    cat = await discord_servers.add_category(1, 100, "Randomizers", "desc", order=2)
    await discord_servers.add_category(2, 200, "Other guild")
    assert [c.category_title for c in await discord_servers.list_categories(1)] == ["Randomizers"]

    await discord_servers.update_category(1, cat.id, "Renamed", None, order=5)
    cat = await models.DiscordServerCategories.get(id=cat.id)
    assert (cat.category_title, cat.category_description, cat.order, cat.channel_id) == ("Renamed", None, 5, 100)

    await discord_servers.remove_category(1, cat.id)
    assert await discord_servers.list_categories(1) == []


async def test_category_and_server_ids_are_scoped_to_guild(db):
    """An admin of guild 2 can't change guild 1's categories or servers by guessing ids
    (this was a known issue until the website editor)."""
    cat = await discord_servers.add_category(1, 100, "Guild one's")
    server = await discord_servers.add_server(1, cat.id, "abc", "A server")
    with pytest.raises(NotFoundError):
        await discord_servers.update_server(2, server.id, "xyz", cat.id, "changed")
    with pytest.raises(NotFoundError):
        await discord_servers.update_category(2, cat.id, "changed", None)
    with pytest.raises(NotFoundError):
        await discord_servers.remove_category(2, cat.id)
    with pytest.raises(NotFoundError):
        await discord_servers.remove_server(2, server.id)
    with pytest.raises(NotFoundError):
        await discord_servers.add_server(2, cat.id, "def", "Sneaky")
    with pytest.raises(NotFoundError):
        await discord_servers.list_servers(2, cat.id)
    assert (await models.DiscordServerLists.get(id=server.id)).invite_id == "abc"
    assert [c.category_title for c in await discord_servers.list_categories(1)] == ["Guild one's"]


async def test_discord_servers_in_category(db):
    cat = await discord_servers.add_category(1, 100, "Randomizers")
    other = await discord_servers.add_category(1, 100, "Other")
    server = await discord_servers.add_server(1, cat.id, "abc", "ALTTPR")
    await discord_servers.add_server(1, other.id, "def", "SM")
    assert [s.invite_id for s in await discord_servers.list_servers(1, cat.id)] == ["abc"]

    await discord_servers.update_server(1, server.id, "xyz", other.id, "ALTTPR 2")
    server = await models.DiscordServerLists.get(id=server.id)
    assert (server.invite_id, server.category_id, server.server_description) == ("xyz", other.id, "ALTTPR 2")
    assert [s.invite_id for s in await discord_servers.list_servers(1, other.id)] == ["def", "xyz"]  # moved to the end

    await discord_servers.remove_server(1, server.id)
    assert [s.invite_id for s in await discord_servers.list_servers(1, other.id)] == ["def"]


async def test_update_server_without_description_keeps_it(db):
    """``/discordservers update_server`` makes the description optional; leaving it out
    keeps the old one (it used to fail on the NOT NULL column)."""
    cat = await discord_servers.add_category(1, 100, "Randomizers")
    server = await discord_servers.add_server(1, cat.id, "abc", "ALTTPR")
    await discord_servers.update_server(1, server.id, "xyz", cat.id)
    server = await models.DiscordServerLists.get(id=server.id)
    assert (server.invite_id, server.server_description) == ("xyz", "ALTTPR")


async def test_server_list_layout_pages_of_ten(db):
    big = await discord_servers.add_category(1, 100, "Big")
    await discord_servers.add_category(1, 200, "Empty")
    small = await discord_servers.add_category(1, 100, "Small")
    await discord_servers.add_category(2, 300, "Other guild")
    for i in range(23):
        await discord_servers.add_server(1, big.id, f"inv{i}", f"Server {i}")
    await discord_servers.add_server(1, small.id, "solo", "Solo")

    layout = await discord_servers.server_list_layout(1)

    assert sorted(layout.channel_ids) == [100, 200]  # the empty category's channel is still cleared
    assert [(p.category_title, p.part, p.part_count, len(p.servers)) for p in layout.pages] == [
        ("Big", 1, 3, 10),
        ("Big", 2, 3, 10),
        ("Big", 3, 3, 3),
        ("Small", 1, 1, 1),
    ]
    assert layout.pages[0].channel_id == 100
    assert layout.pages[2].servers[-1].invite_id == "inv22"


# ---------------------------------------------------------------------------
# voice_roles
# ---------------------------------------------------------------------------


async def test_voice_roles(db):
    vr = await voice_roles.create(1, 10, 20)
    await voice_roles.create(2, 30, 40)
    assert [(v.voice_channel_id, v.role_id) for v in await voice_roles.for_guild(1)] == [(10, 20)]

    await voice_roles.delete(2, vr.id)  # another guild's: no-op
    assert len(await voice_roles.for_guild(1)) == 1
    await voice_roles.delete(1, vr.id)
    assert await voice_roles.for_guild(1) == []


# managing voice roles (web, API, MCP)

VR_GUILD, VR_ADMIN, VR_OWNER = 5, 7, 1


@pytest.fixture
def vr_server(directory):
    directory.owner = VR_OWNER
    directory.add_guild(VR_GUILD, name="Community", admins=[VR_ADMIN],
                        voice_channels=[(10, "Race 1"), (11, "Race 2")],
                        roles=[(20, "@Staff"), (21, "@In Race 1"), (22, "@In Race 2")], unassignable={20})
    return directory


async def test_voice_roles_overview_names_and_flags_problems(db, vr_server):
    await models.VoiceRole.create(guild_id=VR_GUILD, voice_channel_id=11, role_id=22)
    await models.VoiceRole.create(guild_id=VR_GUILD, voice_channel_id=10, role_id=21)
    await models.VoiceRole.create(guild_id=VR_GUILD, voice_channel_id=10, role_id=20)  # above the bot
    await models.VoiceRole.create(guild_id=VR_GUILD, voice_channel_id=99, role_id=21)  # channel deleted
    await models.VoiceRole.create(guild_id=VR_GUILD, voice_channel_id=11, role_id=98)  # role deleted
    await models.VoiceRole.create(guild_id=6, voice_channel_id=10, role_id=21)  # another server's

    data = await voice_roles.overview(VR_GUILD, VR_ADMIN)
    assert [(v["voice_channel_name"], v["role_name"], v["problem"]) for v in data["voice_roles"]] == [
        ("Race 1", "@In Race 1", None),
        ("Race 1", "@Staff", voice_roles.ROLE_UNASSIGNABLE),
        ("Race 2", None, voice_roles.ROLE_GONE),
        ("Race 2", "@In Race 2", None),
        (None, "@In Race 1", voice_roles.CHANNEL_GONE),
    ]
    assert data["voice_channels"] == [{"id": 10, "name": "Race 1"}, {"id": 11, "name": "Race 2"}]
    assert [(r["name"], r["assignable"]) for r in data["roles"]] == [
        ("@Staff", False), ("@In Race 1", True), ("@In Race 2", True)]
    assert (await voice_roles.overview(VR_GUILD, VR_OWNER))["voice_roles"]  # the bot owner may too


async def test_voice_roles_are_admin_only(db, vr_server):
    for call in (voice_roles.overview(VR_GUILD, 42), voice_roles.add(VR_GUILD, 42, 10, 21),
                 voice_roles.remove(VR_GUILD, 42, 1)):
        with pytest.raises(PermissionDeniedError):
            await call
    with pytest.raises(NotFoundError):
        await voice_roles.overview(999, VR_ADMIN)  # the bot isn't in it


async def test_add_voice_role_checks_and_audits(db, vr_server):
    added = await voice_roles.add(VR_GUILD, VR_ADMIN, 10, 21)
    assert (added["voice_channel_name"], added["role_name"], added["problem"]) == ("Race 1", "@In Race 1", None)
    assert [(v.voice_channel_id, v.role_id) for v in await voice_roles.for_guild(VR_GUILD)] == [(10, 21)]
    entry = await models.AuditLog.filter(action="voice_role.created").first()
    assert (entry.guild_id, entry.target) == (VR_GUILD, "Race 1 → @In Race 1")

    for channel, role, message in [(99, 21, "voice channel"), (None, 21, "voice channel"), (10, 98, "Pick a role"),
                                   (10, 20, "can't give @Staff"), (10, 21, "already gives")]:
        with pytest.raises(InvalidInputError, match=message):
            await voice_roles.add(VR_GUILD, VR_ADMIN, channel, role)
    assert len(await voice_roles.for_guild(VR_GUILD)) == 1


async def test_remove_voice_role(db, vr_server):
    other = await models.VoiceRole.create(guild_id=6, voice_channel_id=10, role_id=21)
    added = await voice_roles.add(VR_GUILD, VR_ADMIN, 11, 22)
    with pytest.raises(NotFoundError):
        await voice_roles.remove(VR_GUILD, VR_ADMIN, other.id)  # another server's
    await voice_roles.remove(VR_GUILD, VR_ADMIN, added["id"])
    assert await voice_roles.for_guild(VR_GUILD) == []
    entry = await models.AuditLog.filter(action="voice_role.deleted").first()
    assert entry.target == "Race 2 → @In Race 2"
    with pytest.raises(NotFoundError):
        await voice_roles.remove(VR_GUILD, VR_ADMIN, added["id"])
