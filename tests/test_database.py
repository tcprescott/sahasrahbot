"""Characterization tests for the raw-SQL data access helpers (alttprbot/database/).

Guild config moved to alttprbot/services/guild_config.py; its tests are in
tests/test_guild_config_service.py.

The helpers are written for MySQL (``%s`` placeholders, backticks). The
``raw_sql`` fixture runs them against the in-memory SQLite schema built from
the models, translating ``%s`` to ``?``. Statements that use MySQL-only
syntax can't run there; those tests check the SQL that is sent instead.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import models
from alttprbot.database import discord_server_lists, role, smz3_multiworld, spoiler_races, tournament_results, voicerole
from alttprbot.exceptions import SahasrahBotException

# ---------------------------------------------------------------------------
# alttprbot.database.role (reaction roles)
# ---------------------------------------------------------------------------


async def test_known_issue_reaction_role_description_column_missing(raw_sql):
    """KNOWN ISSUE, pinned not endorsed: ``create_role`` and ``update_role``
    write a ``description`` column that the ReactionRole model and every
    migration lack, so they fail against a schema built from the migrations."""
    from tortoise.exceptions import OperationalError

    await role.create_group(1, 100, 200, "g", "", 1)
    (group,) = await role.get_guild_groups(1)
    with pytest.raises(OperationalError, match="description"):
        await role.create_role(1, group["id"], 999, "they/them", "🟣", "desc", 0)


async def _add_reaction_role(guild_id, group_id, role_id, name, emoji):
    # create_role can't run (see above), so insert the row the way the table allows
    return await models.ReactionRole.create(
        guild_id=guild_id, reaction_group_id=group_id, role_id=role_id, name=name, emoji=emoji, protect_mentions=0
    )


async def test_reaction_role_groups_and_roles(raw_sql):
    await role.create_group(1, 100, 200, "Pronouns", "pick one", 1)
    with pytest.raises(SahasrahBotException, match="Group already exists"):
        await role.create_group(1, 100, 200, "dupe", "", 1)

    (group,) = await role.get_guild_groups(1)
    assert (group["name"], group["channel_id"], group["message_id"]) == ("Pronouns", 100, 200)
    assert await role.get_guild_groups(2) == []

    await _add_reaction_role(1, group["id"], 999, "they/them", "🟣")
    with pytest.raises(SahasrahBotException, match="Emoji already exists"):
        await role.create_role(1, group["id"], 998, "x", "🟣", "", 0)

    assert await role.get_role_by_group_emoji(100, 200, "🟣", 1) == [{"role_id": 999}]
    (r,) = await role.get_group_roles(group["id"], 1)
    assert (await role.get_role(r["id"], 1))["name"] == "they/them"  # get_role returns one row
    assert (await role.get_role_group(r["id"], 1))[0]["message_id"] == 200

    await role.update_group(1, group["id"], "Renamed", "new desc")
    assert (await role.get_guild_group_by_id(group["id"], 1))[0]["name"] == "Renamed"

    await role.delete_role(1, r["id"])
    await role.delete_group(1, group["id"])
    assert await role.get_guild_groups(1) == []


async def test_create_role_in_another_guilds_group_fails(raw_sql):
    await role.create_group(1, 100, 200, "g", "", 1)
    (group,) = await role.get_guild_groups(1)
    with pytest.raises(IndexError):
        await role.create_role(2, group["id"], 1, "x", "🙂", "", 0)


# ---------------------------------------------------------------------------
# alttprbot.database.voicerole
# ---------------------------------------------------------------------------


async def test_voice_roles(raw_sql):
    await voicerole.create_voice_role(1, 10, 20)
    await voicerole.create_voice_role(2, 30, 40)
    assert await voicerole.get_voice_roles_by_guild(1) == [{"guild_id": 1, "voice_channel_id": 10, "role_id": 20}]
    vr = await models.VoiceRole.get(guild_id=1)
    await voicerole.delete_voice_role(1, vr.id)
    assert await voicerole.get_voice_roles_by_guild(1) == []


# ---------------------------------------------------------------------------
# alttprbot.database.smz3_multiworld
# ---------------------------------------------------------------------------


async def test_smz3_multiworld(raw_sql):
    await smz3_multiworld.insert(5, 6, "normal", "smz3")
    row = await smz3_multiworld.fetch(5)
    assert (row["owner_id"], row["status"], row["preset"]) == (6, "STARTED", "normal")

    await smz3_multiworld.update_status(5, "CLOSED")
    assert (await smz3_multiworld.fetch(5, status="CLOSED"))["status"] == "CLOSED"


async def test_known_issue_smz3_multiworld_fetch_cache_ignores_status(raw_sql):
    """KNOWN ISSUE, pinned not endorsed: the cache key is the message id only,
    so a cached result for one status is returned when asking for another."""
    await smz3_multiworld.insert(5, 6, "normal", "smz3")
    assert await smz3_multiworld.fetch(5) is not None
    assert await smz3_multiworld.fetch(5, status="CLOSED") is not None  # row is STARTED

    await smz3_multiworld.update_status(5, "CLOSED")
    assert await smz3_multiworld.fetch(5) is None
    assert await smz3_multiworld.fetch(5, status="CLOSED") is None  # row is CLOSED


# ---------------------------------------------------------------------------
# alttprbot.database.tournament_results
# ---------------------------------------------------------------------------


async def test_tournament_results_lifecycle(raw_sql):
    await tournament_results.insert_tournament_race("alttpr/room-1", "123", "alttpr", permalink="p0")
    active = await tournament_results.get_active_tournament_race("alttpr/room-1")
    assert (active["episode_id"], active["event"], active["permalink"]) == ("123", "alttpr", "p0")
    assert (await tournament_results.get_active_tournament_race_by_episodeid("123"))["srl_id"] == "alttpr/room-1"

    await tournament_results.update_tournament_results_rolled("alttpr/room-1", permalink="p1", week="2")
    assert (await tournament_results.get_active_tournament_race("alttpr/room-1"))["permalink"] == "p1"

    assert [r["srl_id"] for r in await tournament_results.get_unrecorded_races()] == ["alttpr/room-1"]
    await tournament_results.mark_as_written("alttpr/room-1")
    assert await tournament_results.get_unrecorded_races() == []

    await tournament_results.update_tournament_results("alttpr/room-1", status="STARTED")
    assert await tournament_results.get_active_tournament_race("alttpr/room-1") is None  # no longer "active"

    await tournament_results.update_tournament_race_status("alttpr/room-1", "FINISHED")
    assert (await models.TournamentResults.get()).status == "FINISHED"

    await tournament_results.delete_active_tournament_race("alttpr/room-1")  # only deletes status NULL
    assert await models.TournamentResults.exists()
    await tournament_results.delete_active_tournament_race_all("alttpr/room-1")
    assert not await models.TournamentResults.exists()


async def test_record_tournament_results_sql():
    """Double-quoted "RECORDED" is a string in MySQL's default mode; check the SQL only."""
    with mock.patch.object(tournament_results.orm, "execute", mock.AsyncMock()) as execute:
        await tournament_results.record_tournament_results("room", '{"a": 1}')
    sql, args = execute.call_args.args
    assert sql.startswith('UPDATE tournament_results SET status="RECORDED", results_json=%s')
    assert args == ['{"a": 1}', "room"]


# ---------------------------------------------------------------------------
# alttprbot.database.spoiler_races (MySQL-only SQL: checked, not executed)
# ---------------------------------------------------------------------------


async def test_spoiler_races_sql():
    with mock.patch.object(spoiler_races.orm, "execute", mock.AsyncMock()) as execute, mock.patch.object(
        spoiler_races.orm, "select", mock.AsyncMock(return_value=[{"srl_id": "r"}])
    ) as select:
        await spoiler_races.insert_spoiler_race("r", "url", 600)
        assert "ON DUPLICATE KEY UPDATE" in execute.call_args.args[0]
        assert execute.call_args.args[1] == ["r", "url", 600, "url", 600]

        await spoiler_races.start_spoiler_race("r")
        assert "CURRENT_TIMESTAMP()" in execute.call_args.args[0]

        assert await spoiler_races.get_spoiler_race_by_id("r") == {"srl_id": "r"}
        assert await spoiler_races.get_spoiler_race_by_id_started("r") == {"srl_id": "r"}
        assert "TIMESTAMPADD(SECOND,studytime,started)" in select.call_args.args[0]

        select.return_value = []
        assert await spoiler_races.get_spoiler_race_by_id("r") is False
        assert await spoiler_races.get_spoiler_races() == []


async def test_delete_spoiler_race(raw_sql):
    await models.SpoilerRaces.create(srl_id="r", spoiler_url="u", studytime=1)
    await spoiler_races.delete_spoiler_race("r")
    assert not await models.SpoilerRaces.exists()


# ---------------------------------------------------------------------------
# alttprbot.database.discord_server_lists
# ---------------------------------------------------------------------------


async def test_discord_server_lists(raw_sql):
    await discord_server_lists.add_category(1, 50, "Randomizers", "desc", order=2)
    await discord_server_lists.add_category(1, 50, "Other", "desc", order=1)
    cats = await discord_server_lists.get_categories(1)
    assert [c["category_title"] for c in cats] == ["Other", "Randomizers"]  # by order
    randos = cats[1]

    await discord_server_lists.add_server(1, "invite1", randos["id"], "a server")
    await discord_server_lists.add_server(2, "invite2", randos["id"], "wrong guild, ignored")
    (server,) = await discord_server_lists.get_servers_for_category(randos["id"])
    assert server["invite_id"] == "invite1"

    await discord_server_lists.update_server(1, server["id"], "invite9", randos["id"], "renamed")
    assert (await discord_server_lists.get_server(server["id"]))["invite_id"] == "invite9"

    await discord_server_lists.update_category(randos["id"], 1, "Rando", "d", order=0)
    assert (await discord_server_lists.get_category(randos["id"]))["category_title"] == "Rando"

    await discord_server_lists.remove_server(2, server["id"])  # wrong guild: no-op
    assert await discord_server_lists.get_servers_for_category(randos["id"])
    await discord_server_lists.remove_server(1, server["id"])
    assert await discord_server_lists.get_servers_for_category(randos["id"]) == []


async def test_known_issue_remove_category_targets_server_table():
    """KNOWN ISSUE, pinned not endorsed: ``remove_category`` deletes from
    ``discord_server_lists`` (which has no guild_id column) instead of
    ``discord_server_categories``. The cog uses the ORM instead, so this helper
    looks unused."""
    with mock.patch.object(discord_server_lists.orm, "execute", mock.AsyncMock()) as execute:
        await discord_server_lists.remove_category(1, 7)
    assert execute.call_args.args == ("DELETE FROM discord_server_lists WHERE `id`=%s and `guild_id`=%s;", [7, 1])
