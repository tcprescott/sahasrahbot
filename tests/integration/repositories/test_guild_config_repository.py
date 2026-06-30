"""GuildConfigRepository round-trip tests against in-memory SQLite.

See alttprbot/repositories/guild_config_repository.py.
"""

from alttprbot.repositories import GuildConfigRepository


async def test_upsert_get_delete_round_trip(tortoise_db):
    assert await GuildConfigRepository.get(1, "Key") is None

    row, created = await GuildConfigRepository.upsert(1, "Key", "value1")
    assert created is True
    assert row.value == "value1"

    row2, created2 = await GuildConfigRepository.upsert(1, "Key", "value2")
    assert created2 is False
    assert row2.id == row.id

    fetched = await GuildConfigRepository.get(1, "Key")
    assert fetched is not None and fetched.value == "value2"

    deleted = await GuildConfigRepository.delete(1, "Key")
    assert deleted == 1
    assert await GuildConfigRepository.get(1, "Key") is None


async def test_list_for_guild_and_parameter(tortoise_db):
    await GuildConfigRepository.upsert(1, "A", "x")
    await GuildConfigRepository.upsert(1, "B", "y")
    await GuildConfigRepository.upsert(2, "A", "z")

    guild_rows = await GuildConfigRepository.list_for_guild(1)
    assert {r["parameter"] for r in guild_rows} == {"A", "B"}

    param_rows = await GuildConfigRepository.list_for_parameter("A")
    assert {(r["guild_id"], r["value"]) for r in param_rows} == {(1, "x"), (2, "z")}
