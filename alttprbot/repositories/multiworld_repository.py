"""Data access for the ``multiworld`` and ``multiworld_entrant`` tables."""

from typing import List, Optional

from alttprbot import models


class MultiworldRepository:
    @staticmethod
    async def get_by_message_id(message_id: int) -> Optional[models.Multiworld]:
        return await models.Multiworld.get_or_none(message_id=message_id)

    @staticmethod
    async def save(multiworld: models.Multiworld) -> None:
        await multiworld.save()

    @staticmethod
    async def save_fields(multiworld: models.Multiworld, fields: list) -> None:
        await multiworld.save(update_fields=fields)

    # --- entrants ---

    @staticmethod
    async def get_entrant(
        discord_user_id: int, multiworld: models.Multiworld
    ) -> Optional[models.MultiworldEntrant]:
        return await models.MultiworldEntrant.get_or_none(
            discord_user_id=discord_user_id, multiworld=multiworld
        )

    @staticmethod
    async def create_entrant(
        discord_user_id: int, multiworld: models.Multiworld
    ) -> models.MultiworldEntrant:
        return await models.MultiworldEntrant.create(
            discord_user_id=discord_user_id, multiworld=multiworld
        )

    @staticmethod
    async def delete_entrant(entrant: models.MultiworldEntrant) -> None:
        await entrant.delete()

    @staticmethod
    async def list_entrants_by_message_id(message_id: int) -> List[models.MultiworldEntrant]:
        return await models.MultiworldEntrant.filter(multiworld__message_id=message_id)
