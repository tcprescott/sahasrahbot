"""Per-guild settings stored in the ``config`` table.

This is the only module that reads or writes ``models.Config``. Callers pass a guild
id (an int), never a ``discord.Guild``, so the Discord bot, the web app and the
racetime bots can all share it.

Values are strings (``'true'``, a channel id, a comma-separated list of channel
names, …), exactly as stored. Guild id ``0`` holds bot-wide settings.

Reads are cached in memory for ``CACHE_TTL`` seconds; every write through this
module clears the affected keys. A missing setting is cached too, so a guild with
no row does not hit the database on every message.
"""

import aiocache

from alttprbot import models

CACHE_TTL = 300

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)

# aiocache returns ``default`` for a stored None, so values are cached wrapped in a
# one-item tuple to tell "not cached" apart from "cached as not set".


def _value_key(guild_id: int, parameter: str) -> str:
    return f'guildconfig:value:{guild_id}:{parameter}'


def _guild_key(guild_id: int) -> str:
    return f'guildconfig:guild:{guild_id}'


def _parameter_key(parameter: str) -> str:
    return f'guildconfig:parameter:{parameter}'


async def _invalidate(guild_id: int, parameter: str) -> None:
    await CACHE.delete(_value_key(guild_id, parameter))
    await CACHE.delete(_guild_key(guild_id))
    await CACHE.delete(_parameter_key(parameter))


async def get(guild_id: int, parameter: str, default=None):
    """Return the stored value of ``parameter`` for the guild, or ``default``."""
    key = _value_key(guild_id, parameter)
    cached = await CACHE.get(key)
    if cached is None:
        row = await models.Config.get_or_none(guild_id=guild_id, parameter=parameter)
        cached = (None if row is None else row.value,)
        await CACHE.set(key, cached, ttl=CACHE_TTL)
    value = cached[0]
    return default if value is None else value


async def is_enabled(guild_id: int, parameter: str) -> bool:
    """True when the setting is stored as the string ``'true'``."""
    return await get(guild_id, parameter) == 'true'


async def get_list(guild_id: int, parameter: str) -> list[str] | None:
    """Split a comma-separated setting; ``None`` when it isn't set."""
    value = await get(guild_id, parameter)
    if value is None:
        return None
    return [item.strip() for item in value.split(',') if item.strip()]


async def set_value(guild_id: int, parameter: str, value: str) -> None:
    await models.Config.update_or_create(
        guild_id=guild_id, parameter=parameter, defaults={'value': value}
    )
    await _invalidate(guild_id, parameter)


async def delete_value(guild_id: int, parameter: str) -> None:
    await models.Config.filter(guild_id=guild_id, parameter=parameter).delete()
    await _invalidate(guild_id, parameter)


async def for_guild(guild_id: int) -> dict[str, str | None]:
    """Every setting for one guild, as ``{parameter: value}``."""
    key = _guild_key(guild_id)
    values = await CACHE.get(key)
    if values is None:
        rows = await models.Config.filter(guild_id=guild_id)
        values = {row.parameter: row.value for row in rows}
        await CACHE.set(key, values, ttl=CACHE_TTL)
    return dict(values)


async def guilds_with(parameter: str) -> dict[int, str | None]:
    """Every guild that has ``parameter`` set, as ``{guild_id: value}``."""
    key = _parameter_key(parameter)
    values = await CACHE.get(key)
    if values is None:
        rows = await models.Config.filter(parameter=parameter)
        values = {row.guild_id: row.value for row in rows}
        await CACHE.set(key, values, ttl=CACHE_TTL)
    return dict(values)
