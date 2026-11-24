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
from alttprbot.database import role, voicerole
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
