"""The Servers area: alttprbot/services/servers.py and its /api/v1/servers routes."""

from unittest import mock

import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.integrations import holyimage
from alttprbot.services import guild_config, servers
from tests.test_api import CSRF, client, get_json, login, send_json  # noqa: F401 (fixtures)

GUILD = 4100
OTHER = 4200
ADMIN = 41
MEMBER = 42
OWNER = 43


@pytest.fixture
def guilds(directory):
    directory.owner = OWNER
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], members={MEMBER: []},
                        channels=[(300, "#daily"), (301, "#races")], roles=[(77, "@Mods"), (78, "@Racers")],
                        voice_channels=[(400, "Racing VC")], unassignable={77})
    directory.add_guild(OTHER, name="Another", admins=[MEMBER])
    return directory


@pytest.fixture
def games(monkeypatch):
    fake = mock.AsyncMock(return_value={"z3r": [], "smz3": []})
    monkeypatch.setattr(holyimage, "get_holy_images", fake)
    return fake


async def test_admins_and_the_owner_manage_a_server(db, guilds):
    await servers.require_admin(GUILD, ADMIN)
    await servers.require_admin(GUILD, OWNER)
    with pytest.raises(PermissionDeniedError):
        await servers.require_admin(GUILD, MEMBER)
    with pytest.raises(NotFoundError):
        await servers.require_admin(999, OWNER)


async def test_servers_lists_those_the_bot_is_in(db, guilds):
    assert await servers.servers([OTHER, GUILD, 999]) == [{"id": OTHER, "name": "Another"},
                                                          {"id": GUILD, "name": "Community"}]


async def test_settings_read_and_save(db, guilds, games):
    await guild_config.set_value(GUILD, servers.DAILY_ANNOUNCER_CHANNEL, "daily,old-dailies")
    got = await servers.settings(GUILD, ADMIN)
    assert got == {
        "daily_channels": [{"name": "daily", "usable": True}, {"name": "old-dailies", "usable": False}],
        "holy_image_game": None, "holy_image_fallback": "z3r", "holy_image_games": ["smz3", "z3r"],
    }

    # A channel already set may stay; a new one must be somewhere the bot can post.
    with pytest.raises(InvalidInputError, match="#general"):
        await servers.update_settings(GUILD, ADMIN, ["daily", "general"], None)
    with pytest.raises(InvalidInputError, match="no holy images"):
        await servers.update_settings(GUILD, ADMIN, ["races"], "nope")
    assert await guild_config.get(GUILD, servers.DAILY_ANNOUNCER_CHANNEL) == "daily,old-dailies"  # nothing saved

    got = await servers.update_settings(GUILD, ADMIN, ["#races", "old-dailies", "races"], "smz3")
    assert [c["name"] for c in got["daily_channels"]] == ["races", "old-dailies"]
    assert got["holy_image_game"] == "smz3"
    assert await guild_config.get(GUILD, servers.DAILY_ANNOUNCER_CHANNEL) == "races,old-dailies"

    entries = await models.AuditLog.filter(guild_id=GUILD).order_by("id")
    assert [(e.action, e.target) for e in entries] == [
        ("server_setting.changed", "DailyAnnouncerChannel"),
        ("server_setting.changed", "DailyAnnouncerChannel"),
        ("server_setting.changed", "HolyImageDefaultGame"),
    ]

    # Saving the same thing changes nothing; empty turns both back off.
    await servers.update_settings(GUILD, ADMIN, ["races", "old-dailies"], "smz3")
    assert await models.AuditLog.filter(guild_id=GUILD).count() == 3
    got = await servers.update_settings(GUILD, ADMIN, [], "")
    assert got["daily_channels"] == [] and got["holy_image_game"] is None
    assert await guild_config.get(GUILD, servers.DAILY_ANNOUNCER_CHANNEL) is None
    assert await guild_config.get(GUILD, servers.HOLY_IMAGE_DEFAULT_GAME) is None

    with pytest.raises(PermissionDeniedError):
        await servers.update_settings(GUILD, MEMBER, [], None)


async def test_settings_survive_the_holy_image_site_being_down(db, guilds, games):
    games.side_effect = OSError("down")
    got = await servers.update_settings(GUILD, ADMIN, [], "anything")  # can't check, so it's taken
    assert got["holy_image_games"] == [] and got["holy_image_game"] == "anything"


async def test_commas_are_refused(db, guilds, games):
    with pytest.raises(InvalidInputError):
        await servers.update_settings(GUILD, ADMIN, ["a,b"], None)


async def test_api(client, login, guilds, games):
    login(ADMIN)
    assert await get_json(client, "/api/v1/servers") == (200, {"servers": [{"id": str(GUILD), "name": "Community"}]})
    status, body = await get_json(client, f"/api/v1/servers/{GUILD}")
    assert status == 200
    assert body == {
        "id": str(GUILD), "name": "Community",
        "text_channels": [{"id": "300", "name": "#daily"}, {"id": "301", "name": "#races"}],
        "voice_channels": [{"id": "400", "name": "Racing VC"}],
        "roles": [{"id": "77", "name": "@Mods", "position": 2, "assignable": False},
                  {"id": "78", "name": "@Racers", "position": 1, "assignable": True}],
    }

    status, body = await send_json(client, "PUT", f"/api/v1/servers/{GUILD}/settings",
                                   {"daily_channels": ["daily"], "holy_image_game": "smz3"})
    assert status == 200 and body["daily_channels"] == [{"name": "daily", "usable": True}]
    assert (await get_json(client, f"/api/v1/servers/{GUILD}/settings"))[1]["holy_image_game"] == "smz3"
    status, body = await send_json(client, "PUT", f"/api/v1/servers/{GUILD}/settings", {"daily_channels": ["nope"]})
    assert status == 400 and "#nope" in body["error"]

    login(MEMBER)
    assert (await get_json(client, "/api/v1/servers"))[1] == {"servers": [{"id": str(OTHER), "name": "Another"}]}
    assert (await get_json(client, f"/api/v1/servers/{GUILD}"))[0] == 403
    assert (await get_json(client, f"/api/v1/servers/{GUILD}/settings"))[0] == 403
    assert (await send_json(client, "PUT", f"/api/v1/servers/{GUILD}/settings", {"daily_channels": []}))[0] == 403
    assert (await get_json(client, "/api/v1/servers/999"))[0] == 404

    login(None)
    assert (await get_json(client, "/api/v1/servers"))[0] == 401
