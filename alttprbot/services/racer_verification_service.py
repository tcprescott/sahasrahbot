"""Racer-verification configuration service (the verification message + its rules)."""

from typing import List, Optional

from alttprbot import models
from alttprbot.repositories import RacerVerificationRepository


class RacerVerificationService:
    def __init__(self) -> None:
        self.repository = RacerVerificationRepository()

    async def get_by_message_and_guild(
        self, message_id: int, guild_id: int
    ) -> Optional[models.RacerVerification]:
        return await self.repository.get_by_message_and_guild(message_id, guild_id)

    async def list_all(self) -> List[models.RacerVerification]:
        return await self.repository.list_all()

    async def list_by_guild(self, guild_id: int) -> List[models.RacerVerification]:
        return await self.repository.list_by_guild(guild_id)

    async def configure(
        self, *, role_id: int, guild_id: int, defaults: dict
    ) -> models.RacerVerification:
        racer_verification, _ = await self.repository.upsert_by_role_and_guild(
            role_id=role_id, guild_id=guild_id, defaults=defaults
        )
        return racer_verification

    async def set_message(
        self, racer_verification: models.RacerVerification, *, message_id: int, channel_id: int
    ) -> None:
        await self.repository.set_message(
            racer_verification, message_id=message_id, channel_id=channel_id
        )
