"""Voice-role service (deprecated feature; kept for compatibility)."""

from typing import List

from alttprbot import models
from alttprbot.repositories import VoiceRoleRepository


class VoiceRoleService:
    def __init__(self) -> None:
        self.repository = VoiceRoleRepository()

    async def list_for_guild(self, guild_id: int) -> List[models.VoiceRole]:
        return await self.repository.list_for_guild(guild_id)
