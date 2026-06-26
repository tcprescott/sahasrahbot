"""Guild configuration service.

Per-guild key/value settings (the ``config`` table) with an in-memory cache.
This is the canonical replacement for the ``Guild.config_*`` monkey-patch and the
legacy ``alttprbot.database.config`` module (both kept alive as coexisting shims
over the same rows until their remaining callers migrate).

UI-free: channel-name -> id resolution is delegated to a caller-supplied
``resolver`` so the service never imports discord.
"""

from typing import Any, Callable, Dict, List, Optional

import aiocache

from alttprbot.repositories import GuildConfigRepository

# Process-wide cache so all service instances stay coherent with one another.
GUILD_CONFIG_CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)


class GuildConfigService:
    def __init__(self, cache: Optional[aiocache.Cache] = None):
        self.cache = cache or GUILD_CONFIG_CACHE
        self.repository = GuildConfigRepository()

    async def get(self, guild_id: int, parameter: str, default: Any = None) -> Any:
        cache_key = f"{parameter}_{guild_id}_config"
        if await self.cache.exists(cache_key):
            return await self.cache.get(cache_key)

        result = await self.repository.get(guild_id, parameter)
        value = result.value if result is not None else default
        await self.cache.set(cache_key, value)
        return value

    async def set(self, guild_id: int, parameter: str, value: str) -> None:
        await self.repository.upsert(guild_id, parameter, value)
        await self.cache.delete(f"{parameter}_{guild_id}_config")
        await self.cache.delete(f"{guild_id}_guildconfig")

    async def delete(self, guild_id: int, parameter: str) -> None:
        await self.repository.delete(guild_id, parameter)
        await self.cache.delete(f"{parameter}_{guild_id}_config")
        await self.cache.delete(f"{guild_id}_guildconfig")

    async def list(self, guild_id: int) -> List[Dict[str, Any]]:
        cache_key = f"{guild_id}_guildconfig"
        if await self.cache.exists(cache_key):
            return await self.cache.get(cache_key)

        values = await self.repository.list_for_guild(guild_id)
        await self.cache.set(cache_key, values)
        return values

    async def get_all_guilds_with_parameter(self, parameter: str) -> List[Dict[str, Any]]:
        return await self.repository.list_for_parameter(parameter)

    async def get_channel_ids(
        self,
        guild_id: int,
        parameter: str,
        resolver: Callable[[str], Optional[int]],
        default: str = "",
    ) -> List[int]:
        """Resolve a comma-separated channel config value to a list of channel ids.

        Supports both raw ids and channel names; names are resolved via the
        caller-supplied ``resolver`` (``name -> channel id or None``), keeping
        discord lookups in the presentation layer.
        """
        value = await self.get(guild_id, parameter, default)
        if not value:
            return []

        channel_ids: List[int] = []
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            if item.isdigit():
                channel_ids.append(int(item))
            else:
                resolved = resolver(item)
                if resolved is not None:
                    channel_ids.append(resolved)
        return channel_ids
