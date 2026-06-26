"""Multiworld signup service (deprecated feature; kept for compatibility)."""

from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import MultiworldRepository


class MultiworldService:
    def __init__(self) -> None:
        self.repository = MultiworldRepository()

    async def get_for_message(self, message_id: int) -> Optional[models.Multiworld]:
        return await self.repository.get_by_message_id(message_id)

    async def save(self, multiworld: models.Multiworld) -> None:
        await self.repository.save(multiworld)

    async def save_fields(self, multiworld: models.Multiworld, fields: list) -> None:
        await self.repository.save_fields(multiworld, fields)

    async def get_entrant(
        self, discord_user_id: int, multiworld: models.Multiworld
    ) -> Optional[models.MultiworldEntrant]:
        return await self.repository.get_entrant(discord_user_id, multiworld)

    async def add_entrant(
        self, discord_user_id: int, multiworld: models.Multiworld
    ) -> models.MultiworldEntrant:
        return await self.repository.create_entrant(discord_user_id, multiworld)

    async def remove_entrant(self, entrant: models.MultiworldEntrant) -> None:
        await self.repository.delete_entrant(entrant)

    async def list_entrants(self, message_id: int) -> List[models.MultiworldEntrant]:
        return await self.repository.list_entrants_by_message_id(message_id)
