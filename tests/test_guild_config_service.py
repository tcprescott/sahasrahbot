"""Tests for alttprbot/services/guild_config.py, against the in-memory SQLite ``db``.

This replaced the ``discord.Guild`` monkey-patch (alttprbot_discord/util/guild_config.py)
and the raw-SQL accessor (alttprbot/database/config.py). Two behaviours from those
were changed on purpose:

- A missing setting used to be cached with the first caller's default, so a later
  caller passing a different default got the first one. Now each caller gets its own.
- The two old modules shared cache keys with different value shapes. There is now one
  cache, owned here.
"""

from alttprbot import models
from alttprbot.services import guild_config


async def test_roundtrip(db):
    assert await guild_config.get(10, "Missing", default="dflt") == "dflt"

    await guild_config.set_value(10, "Key", "v1")
    assert await guild_config.get(10, "Key") == "v1"
    await guild_config.set_value(10, "Key", "v2")  # update_or_create, cache cleared
    assert await guild_config.get(10, "Key") == "v2"
    assert await guild_config.for_guild(10) == {"Key": "v2"}
    assert await models.Config.filter(guild_id=10).count() == 1

    await guild_config.delete_value(10, "Key")
    assert await guild_config.get(10, "Key") is None
    assert await guild_config.for_guild(10) == {}


async def test_reads_are_cached(db):
    await guild_config.set_value(1, "Foo", "bar")
    assert await guild_config.get(1, "Foo") == "bar"
    await models.Config.filter(guild_id=1).update(value="changed-behind-the-cache")
    assert await guild_config.get(1, "Foo") == "bar"


async def test_missing_value_uses_each_callers_default(db):
    assert await guild_config.get(10, "Key", default="first") == "first"
    assert await guild_config.get(10, "Key", default="second") == "second"
    assert await guild_config.get(10, "Key") is None
    # The miss is still cached: a row written behind the cache isn't seen yet.
    await models.Config.create(guild_id=10, parameter="Key", value="late")
    assert await guild_config.get(10, "Key") is None


async def test_set_value_clears_every_cached_view(db):
    assert await guild_config.is_enabled(1, "TournamentEnabled") is False
    assert await guild_config.for_guild(1) == {}
    assert await guild_config.guilds_with("TournamentEnabled") == {}

    await guild_config.set_value(1, "TournamentEnabled", "true")

    assert await guild_config.is_enabled(1, "TournamentEnabled") is True
    assert await guild_config.for_guild(1) == {"TournamentEnabled": "true"}
    assert await guild_config.guilds_with("TournamentEnabled") == {1: "true"}


async def test_settings_are_per_guild(db):
    await guild_config.set_value(1, "DailyAnnouncerChannel", "daily")
    await guild_config.set_value(2, "DailyAnnouncerChannel", "races,daily")
    await guild_config.set_value(2, "CommandPrefix", "!")

    assert await guild_config.get(3, "DailyAnnouncerChannel") is None
    assert await guild_config.guilds_with("DailyAnnouncerChannel") == {1: "daily", 2: "races,daily"}
    assert await guild_config.for_guild(2) == {"DailyAnnouncerChannel": "races,daily", "CommandPrefix": "!"}


async def test_get_list_splits_comma_separated_values(db):
    await guild_config.set_value(1, "Channels", "general, races,,")

    assert await guild_config.get_list(1, "Channels") == ["general", "races"]
    assert await guild_config.get_list(1, "Unset") is None
