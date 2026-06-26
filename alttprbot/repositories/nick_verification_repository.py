"""Data access for the ``nick_verification`` table."""

from alttprbot import models


class NickVerificationRepository:
    @staticmethod
    async def delete_by_discord_id(discord_user_id: int) -> int:
        return await models.NickVerification.filter(discord_user_id=discord_user_id).delete()
