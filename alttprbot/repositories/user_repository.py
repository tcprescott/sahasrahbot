"""Data access for the ``users`` table, including account merges."""

from typing import Optional, Tuple

from alttprbot import models


class UserRepository:
    @staticmethod
    async def get_by_rtgg_id(rtgg_id: str) -> Optional[models.Users]:
        return await models.Users.get_or_none(rtgg_id=rtgg_id)

    @staticmethod
    async def get_by_discord_id(discord_user_id: int) -> Optional[models.Users]:
        return await models.Users.get_or_none(discord_user_id=discord_user_id)

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[models.Users]:
        return await models.Users.get_or_none(id=user_id)

    @staticmethod
    async def get_or_create_by_discord_id(
        discord_user_id: int, *, display_name: str
    ) -> Tuple[models.Users, bool]:
        return await models.Users.get_or_create(
            discord_user_id=discord_user_id, defaults={"display_name": display_name}
        )

    @staticmethod
    async def upsert_by_discord_id(discord_user_id: int, defaults: dict) -> Tuple[models.Users, bool]:
        return await models.Users.update_or_create(discord_user_id=discord_user_id, defaults=defaults)

    @staticmethod
    async def upsert_by_rtgg_id(rtgg_id: str, defaults: dict) -> Tuple[models.Users, bool]:
        return await models.Users.update_or_create(rtgg_id=rtgg_id, defaults=defaults)

    @staticmethod
    async def merge(user_to_keep: models.Users, victim: models.Users) -> models.Users:
        """Fold ``victim`` into ``user_to_keep``: adopt ids, reassign owned rows, delete victim.

        Preserves the original racetime-verification merge behavior exactly.
        """
        if victim.discord_user_id:
            user_to_keep.discord_user_id = victim.discord_user_id
        if victim.rtgg_id:
            user_to_keep.rtgg_id = victim.rtgg_id

        await models.AsyncTournamentAuditLog.filter(user=victim).update(user=user_to_keep)
        await models.AsyncTournamentPermissions.filter(user=victim).update(user=user_to_keep)
        await models.AsyncTournamentRace.filter(user=victim).update(user=user_to_keep)
        await models.AsyncTournamentRace.filter(reviewed_by=victim).update(reviewed_by=user_to_keep)
        await models.AsyncTournamentReviewNotes.filter(author=victim).update(author=user_to_keep)

        await victim.delete()
        await user_to_keep.save()
        return user_to_keep
