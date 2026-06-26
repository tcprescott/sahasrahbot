"""Data access for the ``config`` table (per-guild key/value settings)."""

from typing import Any, Dict, List, Optional, Tuple

from alttprbot import models


class GuildConfigRepository:
    @staticmethod
    async def get(guild_id: int, parameter: str) -> Optional[models.Config]:
        return await models.Config.get_or_none(guild_id=guild_id, parameter=parameter)

    @staticmethod
    async def upsert(guild_id: int, parameter: str, value: str) -> Tuple[models.Config, bool]:
        return await models.Config.update_or_create(
            guild_id=guild_id, parameter=parameter, defaults={"value": value}
        )

    @staticmethod
    async def delete(guild_id: int, parameter: str) -> int:
        return await models.Config.filter(guild_id=guild_id, parameter=parameter).delete()

    @staticmethod
    async def list_for_guild(guild_id: int) -> List[Dict[str, Any]]:
        return await models.Config.filter(guild_id=guild_id).values()

    @staticmethod
    async def list_for_parameter(parameter: str) -> List[Dict[str, Any]]:
        return await models.Config.filter(parameter=parameter).values()
