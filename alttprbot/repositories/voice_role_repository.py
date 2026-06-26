"""Data access for the ``voice_role`` table."""

from typing import List

from alttprbot import models


class VoiceRoleRepository:
    @staticmethod
    async def list_for_guild(guild_id: int) -> List[models.VoiceRole]:
        return await models.VoiceRole.filter(guild_id=guild_id)
