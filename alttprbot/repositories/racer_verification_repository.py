"""Data access for the ``racer_verification`` table."""

from typing import List, Optional, Tuple

from alttprbot import models


class RacerVerificationRepository:
    @staticmethod
    async def get_by_message_and_guild(
        message_id: int, guild_id: int
    ) -> Optional[models.RacerVerification]:
        return await models.RacerVerification.get_or_none(
            message_id=message_id, guild_id=guild_id
        )

    @staticmethod
    async def list_all() -> List[models.RacerVerification]:
        return await models.RacerVerification.all()

    @staticmethod
    async def list_by_guild(guild_id: int) -> List[models.RacerVerification]:
        return await models.RacerVerification.filter(guild_id=guild_id)

    @staticmethod
    async def upsert_by_role_and_guild(
        *, role_id: int, guild_id: int, defaults: dict
    ) -> Tuple[models.RacerVerification, bool]:
        return await models.RacerVerification.update_or_create(
            role_id=role_id, guild_id=guild_id, defaults=defaults
        )

    @staticmethod
    async def set_message(
        racer_verification: models.RacerVerification, *, message_id: int, channel_id: int
    ) -> None:
        racer_verification.message_id = message_id
        racer_verification.channel_id = channel_id
        await racer_verification.save()
