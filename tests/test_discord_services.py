"""Tests for the services behind the Discord cogs: multiworld (/smmulti), the Discord
server list (/discordservers), reaction roles ($rr/$rg) and voice roles.

They pin what the cogs did before their data access moved into ``alttprbot/services/``.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import models
from alttprbot.exceptions import SahasrahBotException
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

    await discord_servers.update_category(cat.id, "Renamed", None, order=5)
    cat = await models.DiscordServerCategories.get(id=cat.id)
    assert (cat.category_title, cat.category_description, cat.order) == ("Renamed", None, 5)

    await discord_servers.remove_category(cat.id)
    assert await discord_servers.list_categories(1) == []


async def test_known_issue_category_and_server_ids_are_not_scoped_to_guild(db):
    """KNOWN ISSUE, pinned not endorsed: remove/update by id don't check the guild, so an
    admin of one guild can change another guild's categories and servers by guessing ids."""
    cat = await discord_servers.add_category(1, 100, "Guild one's")
    server = await discord_servers.add_server(1, cat.id, "abc", "A server")
    # the cog calls these from guild 2, but the guild is never passed
    await discord_servers.update_server(server.id, "xyz", cat.id, "changed")
    await discord_servers.update_category(cat.id, "changed", None)
    assert (await models.DiscordServerLists.get(id=server.id)).invite_id == "xyz"
    await discord_servers.remove_category(cat.id)
    assert await discord_servers.list_categories(1) == []


async def test_discord_servers_in_category(db):
    cat = await discord_servers.add_category(1, 100, "Randomizers")
    other = await discord_servers.add_category(1, 100, "Other")
    server = await discord_servers.add_server(1, cat.id, "abc", "ALTTPR")
    await discord_servers.add_server(1, other.id, "def", "SM")
    assert [s.invite_id for s in await discord_servers.list_servers(cat.id)] == ["abc"]

    await discord_servers.update_server(server.id, "xyz", other.id, "ALTTPR 2")
    server = await models.DiscordServerLists.get(id=server.id)
    assert (server.invite_id, server.category_id, server.server_description) == ("xyz", other.id, "ALTTPR 2")

    await discord_servers.remove_server(server.id)
    assert [s.invite_id for s in await discord_servers.list_servers(other.id)] == ["def"]


async def test_known_issue_update_server_without_description_fails(db):
    """KNOWN ISSUE, pinned not endorsed: ``/discordservers update_server`` makes the
    description optional, but the column is NOT NULL, so leaving it out fails."""
    from tortoise.exceptions import ValidationError

    cat = await discord_servers.add_category(1, 100, "Randomizers")
    server = await discord_servers.add_server(1, cat.id, "abc", "ALTTPR")
    with pytest.raises(ValidationError, match="server_description"):
        await discord_servers.update_server(server.id, "xyz", cat.id)


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
